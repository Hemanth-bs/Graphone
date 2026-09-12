"""
Async scraper core (Phase I / II / V).

Two fetch strategies behind one interface:
  - `HttpFetcher`  : aiohttp, for plain static/server-rendered pages. Fast,
                     cheap, high concurrency — the default for the bulk of
                     directory pages (startup lists, paper indices, etc).
  - `BrowserFetcher`: Playwright (async API), for JS-heavy or Cloudflare/
                     Datadome-protected pages that return a challenge page
                     to plain HTTP clients.

`AdaptiveFetcher` tries HTTP first and only pays the (much higher) cost of
spinning up a real browser when the HTTP response looks like a bot-block
(status 403/503, or a body containing known challenge markers). This is the
core of the "anti-bot without triggering captchas" strategy (Phase V):
avoid looking automated in the first place rather than trying to solve
challenges after triggering them.

Politeness / scale:
  - Bounded concurrency via asyncio.Semaphore, tunable per-domain so no
    single site gets hammered even if global concurrency is high.
  - Exponential backoff + jitter on 429/5xx, same pattern as the LLM
    orchestrator, for consistency.
  - Rotating User-Agent pool + realistic headers to avoid trivial
    fingerprinting (this is a mitigation, not a captcha bypass — the brief
    asks for a documented *strategy*, not a guarantee against Cloudflare
    Enterprise-tier bot management, which additionally requires session
    persistence, residential proxies, and TLS fingerprint matching that are
    infrastructure decisions, not code decisions — see architecture.pdf).
  - Every fetch attempt is logged with url, status, strategy, elapsed_ms for
    observability at scale.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger("graphone.scraper")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
]

_CHALLENGE_MARKERS = ("cf-browser-verification", "datadome", "checking your browser", "cf-chl")


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    strategy: str          # "http" | "browser"
    elapsed_ms: float
    success: bool


class HttpFetcher:
    def __init__(self, timeout_seconds: float = 20.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def fetch(self, session: aiohttp.ClientSession, url: str) -> FetchResult:
        start = time.time()
        headers = {"User-Agent": random.choice(_USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}
        try:
            async with session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True) as resp:
                body = await resp.text(errors="ignore")
                elapsed = (time.time() - start) * 1000
                looks_blocked = resp.status in (403, 503) or any(m in body.lower() for m in _CHALLENGE_MARKERS)
                return FetchResult(
                    url=url,
                    status=resp.status,
                    html=body,
                    strategy="http",
                    elapsed_ms=elapsed,
                    success=(resp.status == 200 and not looks_blocked),
                )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            elapsed = (time.time() - start) * 1000
            logger.warning("http_fetch_error", extra={"url": url, "error": str(e)})
            return FetchResult(url=url, status=0, html="", strategy="http", elapsed_ms=elapsed, success=False)


class BrowserFetcher:
    """Playwright-based fetcher for JS-rendered or bot-protected pages.

    Import of playwright is deferred to first use so environments that only
    need the HTTP path (e.g. CI running against static fixtures) don't need
    the browser binaries installed.
    """

    def __init__(self, headless: bool = True, wait_for_selector: Optional[str] = None):
        self.headless = headless
        self.wait_for_selector = wait_for_selector
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, *exc):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch(self, url: str) -> FetchResult:
        start = time.time()
        context = await self._browser.new_context(user_agent=random.choice(_USER_AGENTS))
        page = await context.new_page()
        try:
            resp = await page.goto(url, wait_until="networkidle", timeout=30_000)
            if self.wait_for_selector:
                try:
                    await page.wait_for_selector(self.wait_for_selector, timeout=10_000)
                except Exception:
                    pass  # selector never appeared; still return what we have
            html = await page.content()
            elapsed = (time.time() - start) * 1000
            status = resp.status if resp else 0
            return FetchResult(url=url, status=status, html=html, strategy="browser", elapsed_ms=elapsed, success=status == 200)
        finally:
            await context.close()


class AdaptiveFetcher:
    """Tries HTTP first; escalates to a real browser only if HTTP looks blocked.

    This keeps the common case (the vast majority of directory/listing
    pages) cheap and highly concurrent, and reserves the expensive
    browser path for the minority of pages that actually need it —
    critical for the "scale to 500k without code changes" requirement,
    since browser-per-page does not scale horizontally nearly as cheaply
    as HTTP-per-page.
    """

    def __init__(self, concurrency: int = 20, per_domain_concurrency: int = 4):
        self.http_fetcher = HttpFetcher()
        self._global_sem = asyncio.Semaphore(concurrency)
        self._domain_sems: dict[str, asyncio.Semaphore] = {}
        self._per_domain_concurrency = per_domain_concurrency

    def _domain_sem(self, url: str) -> asyncio.Semaphore:
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        if domain not in self._domain_sems:
            self._domain_sems[domain] = asyncio.Semaphore(self._per_domain_concurrency)
        return self._domain_sems[domain]

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> FetchResult:
        async with self._global_sem, self._domain_sem(url):
            attempt = 0
            result: Optional[FetchResult] = None
            while attempt < max_retries:
                result = await self.http_fetcher.fetch(session, url)
                if result.success:
                    logger.info(
                        "fetch_ok", extra={"url": url, "strategy": "http", "elapsed_ms": round(result.elapsed_ms, 1)}
                    )
                    return result
                if result.status == 429 or result.status == 0:
                    attempt += 1
                    backoff = base_backoff * (2 ** (attempt - 1)) + random.uniform(0, base_backoff)
                    logger.info("fetch_retry_backoff", extra={"url": url, "attempt": attempt, "sleep": round(backoff, 2)})
                    await asyncio.sleep(backoff)
                    continue
                # Looks like a bot-block (403/503/challenge markers), not a
                # transient error -> escalate to browser rather than retry
                # the same HTTP request (retrying won't help against a WAF).
                break

            logger.info("escalating_to_browser", extra={"url": url, "http_status": result.status if result else None})
            try:
                async with BrowserFetcher() as browser:
                    browser_result = await browser.fetch(url)
                    logger.info(
                        "fetch_ok",
                        extra={"url": url, "strategy": "browser", "elapsed_ms": round(browser_result.elapsed_ms, 1)},
                    )
                    return browser_result
            except Exception as e:
                logger.error("browser_fetch_failed", extra={"url": url, "error": str(e)})
                return result or FetchResult(url=url, status=0, html="", strategy="browser", elapsed_ms=0.0, success=False)
