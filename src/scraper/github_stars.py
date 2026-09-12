"""
Fetches *current* GitHub star counts for repos associated with research
papers (Phase I requirement: "extract dynamic metrics like current GitHub
stars"). Uses the public GitHub REST API rather than scraping the repo page
HTML — it's rate-limit-transparent (returns exact remaining quota in
headers), returns clean JSON, and is far less likely to break on markup
changes.

Unauthenticated: 60 requests/hour. Set GITHUB_TOKEN env var to raise this to
5,000/hour, which is what you'd want for a run touching thousands of papers.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

import aiohttp

logger = logging.getLogger("graphone.scraper.github")

_REPO_URL_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def parse_owner_repo(github_url: str) -> Optional[tuple[str, str]]:
    match = _REPO_URL_RE.search(github_url.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


async def fetch_star_count(session: aiohttp.ClientSession, github_url: str) -> Optional[int]:
    parsed = parse_owner_repo(github_url)
    if not parsed:
        logger.warning("unparseable_github_url", extra={"url": github_url})
        return None
    owner, repo = parsed

    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 404:
                logger.info("repo_not_found", extra={"url": github_url})
                return None
            if resp.status == 403:
                remaining = resp.headers.get("X-RateLimit-Remaining")
                logger.warning("github_rate_limited", extra={"remaining": remaining})
                return None
            resp.raise_for_status()
            data = await resp.json()
            return data.get("stargazers_count")
    except aiohttp.ClientError as e:
        logger.warning("github_api_error", extra={"url": github_url, "error": str(e)})
        return None
