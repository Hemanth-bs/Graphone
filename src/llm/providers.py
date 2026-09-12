"""
Thin async wrappers around each LLM provider used in the fallback chain.

Each provider implements the same interface — `complete(prompt) -> str` —
and raises one of our normalized exceptions so the orchestrator never has
to know provider-specific error shapes.

Fallback chain (per assignment): Gemini Flash -> Groq Llama 3 -> DeepSeek.

Auth: every provider reads its API key from an environment variable. We
never hardcode keys. If a key is missing, the provider is skipped rather
than crashing the whole chain (a provider being unconfigured shouldn't take
down the pipeline).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx


class LLMError(Exception):
    """Base class for normalized provider errors."""


class RateLimitError(LLMError):
    """Normalized 429 Too Many Requests."""


class PayloadTooLargeError(LLMError):
    """Normalized 413 Payload Too Large (or provider-specific context-length error)."""


class ProviderUnavailableError(LLMError):
    """Provider not configured (missing API key) or unreachable (5xx/network)."""


class BaseProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        ...

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 429:
            raise RateLimitError(f"{self.name}: 429 rate limited")
        if resp.status_code == 413:
            raise PayloadTooLargeError(f"{self.name}: 413 payload too large")
        if resp.status_code >= 500:
            raise ProviderUnavailableError(f"{self.name}: {resp.status_code} server error")
        if resp.status_code == 400:
            # Some providers (e.g. context length exceeded) return 400 instead of 413.
            body = resp.text.lower()
            if "context" in body or "too long" in body or "maximum" in body:
                raise PayloadTooLargeError(f"{self.name}: 400 context-length exceeded")
        resp.raise_for_status()


class GeminiFlashProvider(BaseProvider):
    name = "gemini-flash"
    MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key or os.environ.get("GEMINI_API_KEY"))

    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        if not self.is_configured:
            raise ProviderUnavailableError("gemini-flash: GEMINI_API_KEY not set")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.MODEL}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }
        resp = await client.post(url, json=payload, timeout=timeout)
        self._raise_for_status(resp)
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class GroqLlamaProvider(BaseProvider):
    name = "groq-llama3"
    MODEL = "llama3-70b-8192"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key or os.environ.get("GROQ_API_KEY"))

    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        if not self.is_configured:
            raise ProviderUnavailableError("groq-llama3: GROQ_API_KEY not set")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        resp = await client.post(url, json=payload, headers=headers, timeout=timeout)
        self._raise_for_status(resp)
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    MODEL = "deepseek-chat"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key or os.environ.get("DEEPSEEK_API_KEY"))

    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        if not self.is_configured:
            raise ProviderUnavailableError("deepseek: DEEPSEEK_API_KEY not set")
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        resp = await client.post(url, json=payload, headers=headers, timeout=timeout)
        self._raise_for_status(resp)
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def default_chain() -> list[BaseProvider]:
    """The assignment's specified fallback order."""
    return [GeminiFlashProvider(), GroqLlamaProvider(), DeepSeekProvider()]
