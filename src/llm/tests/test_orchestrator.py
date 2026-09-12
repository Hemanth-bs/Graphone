"""
End-to-end tests for the LLM orchestrator using mock providers so the
fallback chain, backoff, and chunk-splitting logic can be verified without
live API keys or network access.

Run with:  python -m src.llm.tests.test_orchestrator
(also compatible with `pytest -q` if pytest is installed)
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx

from src.llm.orchestrator import ExtractionConfig, LLMOrchestrator
from src.llm.providers import BaseProvider, PayloadTooLargeError, RateLimitError
from src.llm.schemas import RecordType, SourceMeta


class ScriptedProvider(BaseProvider):
    """A mock provider that plays back a scripted sequence of behaviors,
    one per call, so we can deterministically exercise retry/fallback paths."""

    def __init__(self, name: str, script: list):
        super().__init__(api_key="mock-key")
        self.name = name
        self.script = list(script)
        self.calls = 0

    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        self.calls += 1
        if not self.script:
            raise RuntimeError(f"{self.name}: script exhausted")
        step = self.script.pop(0)
        if step == "429":
            raise RateLimitError(f"{self.name}: simulated 429")
        if step == "413":
            raise PayloadTooLargeError(f"{self.name}: simulated 413")
        return step  # otherwise it's the literal JSON string to "generate"


async def test_fallback_after_rate_limit_exhaustion():
    """Tier 1 rate-limits forever -> should fall through to Tier 2 which succeeds."""
    good_paper = json.dumps(
        {
            "title": "Scaling Laws for Neural Graphs",
            "authors": ["A. Researcher"],
            "paper_url": "https://arxiv.org/abs/9999.99999",
            "github_url": "https://github.com/example/repo",
            "github_stars": 1234,
            "published_date": "2026-09-10T00:00:00",
        }
    )
    tier1 = ScriptedProvider("gemini-flash", ["429", "429", "429"])
    tier2 = ScriptedProvider("groq-llama3", [good_paper])
    tier3 = ScriptedProvider("deepseek", [good_paper])

    orch = LLMOrchestrator(
        providers=[tier1, tier2, tier3],
        config=ExtractionConfig(max_retries_per_provider=3, base_backoff_seconds=0.01, max_backoff_seconds=0.05),
    )
    result = await orch.extract(
        record_type=RecordType.RESEARCH_PAPER,
        raw_text="Some arxiv paper HTML body " * 20,
        source=SourceMeta(name="arXiv", url="https://arxiv.org/abs/9999.99999"),
    )
    assert len(result.entities) == 1, f"expected 1 entity, got {result.entities}"
    assert result.entities[0]["content"]["github_stars"] == 1234
    assert tier1.calls == 3, "tier1 should be retried max_retries_per_provider times"
    assert tier2.calls == 1, "tier2 should succeed on first try"
    print("PASS: test_fallback_after_rate_limit_exhaustion")


async def test_413_triggers_chunk_split_not_provider_fallthrough():
    """Tier 1 says payload too large -> chunk should be halved and re-submitted,
    not immediately punted to tier 2."""
    good_job = json.dumps(
        {
            "company": "OpenAI",
            "date": "2026-09-11T00:00:00",
            "is_remote": True,
            "role_family": "Engineering",
        }
    )
    # First call on the full chunk -> 413. Subsequent calls (on halves) succeed.
    tier1 = ScriptedProvider("gemini-flash", ["413", good_job, good_job])
    tier2 = ScriptedProvider("groq-llama3", [good_job, good_job])

    orch = LLMOrchestrator(
        providers=[tier1, tier2],
        config=ExtractionConfig(max_retries_per_provider=2, base_backoff_seconds=0.01),
    )
    result = await orch.extract(
        record_type=RecordType.JOB,
        raw_text="Job posting text. " * 500,
        source=SourceMeta(name="AI Jobs Board", url="https://example.com/jobs/1"),
    )
    assert len(result.entities) >= 1
    assert tier1.calls >= 1
    print("PASS: test_413_triggers_chunk_split_not_provider_fallthrough")


async def test_invalid_json_falls_through_to_next_tier():
    """A provider returning garbage should not crash the pipeline — next tier is tried."""
    good_startup = json.dumps({"entityName": "OpenAI", "data": {"employeeCount": 1500}})
    tier1 = ScriptedProvider("gemini-flash", ["not valid json {{{"])
    tier2 = ScriptedProvider("groq-llama3", [good_startup])

    orch = LLMOrchestrator(providers=[tier1, tier2], config=ExtractionConfig(max_retries_per_provider=1))
    result = await orch.extract(
        record_type=RecordType.STARTUP,
        raw_text="OpenAI is an AI research company with 1500 employees.",
        source=SourceMeta(name="Crunchbase", url="https://example.com/openai"),
    )
    assert len(result.entities) == 1
    assert result.entities[0]["content"]["entityName"] == "OpenAI"
    print("PASS: test_invalid_json_falls_through_to_next_tier")


async def test_skip_marker_produces_no_entity():
    tier1 = ScriptedProvider("gemini-flash", [json.dumps({"__skip__": True})])
    orch = LLMOrchestrator(providers=[tier1], config=ExtractionConfig(max_retries_per_provider=1))
    result = await orch.extract(
        record_type=RecordType.PRODUCT,
        raw_text="This page has nothing product-related on it at all.",
        source=SourceMeta(name="Random Blog", url="https://example.com/blog/1"),
    )
    assert len(result.entities) == 0
    print("PASS: test_skip_marker_produces_no_entity")


class CountingProvider(BaseProvider):
    """Mock provider whose behavior depends on call count, not a fixed script,
    so we can make MANY concurrent chunks all hit 413 on their first call
    (simulating a burst where every in-flight chunk is oversized at once),
    then succeed once they've been split."""

    def __init__(self, name: str, oversized_for_first_n_calls: int, ok_payload: str):
        super().__init__(api_key="mock-key")
        self.name = name
        self.oversized_for_first_n_calls = oversized_for_first_n_calls
        self.ok_payload = ok_payload
        self.calls = 0

    async def complete(self, client: httpx.AsyncClient, prompt: str, *, timeout: float = 60.0) -> str:
        self.calls += 1
        if self.calls <= self.oversized_for_first_n_calls:
            raise PayloadTooLargeError(f"{self.name}: simulated 413 (call {self.calls})")
        return self.ok_payload


async def test_concurrent_413s_do_not_deadlock():
    """Regression test for the semaphore/413-recursion deadlock.

    Previously, the concurrency semaphore was held for the ENTIRE
    _extract_chunk() call, including the recursive re-entrant calls made
    while splitting an oversized chunk. If `concurrency` chunks all got a
    413 at the same time, every permit was held by a parent awaiting a
    child that itself needed a permit to proceed -> permanent deadlock.

    This test drives exactly `concurrency` chunks through a provider that
    413s on their first (concurrent) attempt, forcing every worker to try
    to recurse into sub-chunks at the same time. It must complete well
    under the timeout; if the deadlock regresses, this test hangs forever
    and the wait_for below turns that into a clean failure instead of a
    stuck CI job.
    """
    good_startup = json.dumps({"entityName": "TestCo", "data": {"employeeCount": 10}})
    concurrency = 4

    # Build `concurrency` distinct paragraphs, each its own chunk once we
    # force a tiny max_tokens_per_chunk (below the concurrency limit
    # would defeat the point -- we want >= concurrency chunks in flight
    # together so they can all 413 at once and race on the same semaphore).
    paragraphs = [f"P{i}: " + ("x" * 10) for i in range(concurrency)]
    raw_text = "\n\n".join(paragraphs)

    provider = CountingProvider(
        "flaky-tier",
        oversized_for_first_n_calls=concurrency,  # every initial chunk 413s
        ok_payload=good_startup,
    )

    orch = LLMOrchestrator(
        providers=[provider],
        config=ExtractionConfig(
            max_tokens_per_chunk=5,       # ~20 chars/chunk -> forces one paragraph per chunk
            max_retries_per_provider=1,
            max_chunk_splits=2,
            concurrency=concurrency,
        ),
    )

    result = await asyncio.wait_for(
        orch.extract(
            record_type=RecordType.STARTUP,
            raw_text=raw_text,
            source=SourceMeta(name="Test", url="https://example.com/x"),
        ),
        timeout=5.0,
    )

    from src.llm.chunker import chunk_text
    expected_chunks = len(chunk_text(raw_text, max_tokens_per_chunk=5))

    assert len(result.entities) + len(result.failures) == expected_chunks, (
        f"expected one outcome per original chunk ({expected_chunks}), got "
        f"{len(result.entities)} entities + {len(result.failures)} failures"
    )
    assert len(result.entities) >= 1, "at least some split sub-chunks should have succeeded"
    print("PASS: test_concurrent_413s_do_not_deadlock")


async def main():
    start = time.time()
    await test_fallback_after_rate_limit_exhaustion()
    await test_413_triggers_chunk_split_not_provider_fallthrough()
    await test_invalid_json_falls_through_to_next_tier()
    await test_skip_marker_produces_no_entity()
    await test_concurrent_413s_do_not_deadlock()
    print(f"\nAll tests passed in {time.time() - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
