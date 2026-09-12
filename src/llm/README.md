# LLM Extraction Orchestrator

Multi-tier LLM extraction engine for the GraphOne / FrontierAtlas ingestion
pipeline (Phase III of the assignment).

## Files

- `schemas.py` — pydantic models mirroring the canonical Startup / Product /
  ResearchPaper / Job schemas exactly as specified in the brief.
- `chunker.py` — semantic, boundary-aware text chunking that keeps every
  payload under the tightest provider's token limit, preventing 413s
  proactively rather than just reacting to them.
- `prompts.py` — schema-locked prompt construction. The LLM is only ever
  asked to produce the `content` sub-object; `source`, `collectedAt`, and
  `schemaVersion` are always injected deterministically from real scrape
  metadata. This is the main anti-hallucination guardrail — the model
  literally cannot invent a source URL.
- `providers.py` — async wrappers for Gemini Flash, Groq Llama 3, and
  DeepSeek. Normalizes each provider's error shapes into `RateLimitError`,
  `PayloadTooLargeError`, and `ProviderUnavailableError` so the orchestrator
  logic is provider-agnostic.
- `orchestrator.py` — ties it together:
  - **429 handling**: exponential backoff with jitter, up to
    `max_retries_per_provider` attempts, before falling through to the next
    tier in the chain.
  - **413 handling**: the *same* provider is retried first with the chunk
    halved (cheaper than switching tiers), recursing up to
    `max_chunk_splits` times before falling through.
  - **Validation**: every LLM response is parsed and validated against the
    pydantic schema before being accepted; invalid JSON or failed
    validation falls through to the next provider rather than corrupting
    output.
  - **Concurrency**: bounded by an `asyncio.Semaphore` (`config.concurrency`)
    so thousands of chunks can be in flight without overwhelming providers.
  - **Logging**: every attempt, retry, fallback, and failure is logged with
    structured `extra=` fields (provider, chunk index, attempt count) for
    observability at scale.

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
export GROQ_API_KEY=...
export DEEPSEEK_API_KEY=...
```

Any subset of keys can be set — unconfigured providers are skipped, not
treated as hard failures, so the chain degrades gracefully (e.g. if only
Groq is configured, extraction still works, just without the Gemini tier).

## Usage

```python
import asyncio
from src.llm import LLMOrchestrator, RecordType, SourceMeta

async def main():
    orch = LLMOrchestrator()
    result = await orch.extract(
        record_type=RecordType.RESEARCH_PAPER,
        raw_text=scraped_html,
        source=SourceMeta(name="arXiv", url="https://arxiv.org/abs/1234.5678"),
    )
    for entity in result.entities:
        print(entity)   # matches canonical schema exactly
    for failure in result.failures:
        print("FAILED:", failure)  # feed into a dead-letter queue for reprocessing

asyncio.run(main())
```

## Testing without live API keys

`tests/test_orchestrator.py` uses scripted mock providers to deterministically
exercise the fallback chain, backoff, and chunk-splitting logic without any
network calls or API keys:

```bash
python -m src.llm.tests.test_orchestrator
```

## Design notes / trade-offs

- **Chunk size is set to the tightest tier's limit, not each provider's own
  limit.** This means Gemini (which could take larger payloads) is
  slightly underutilized, but it guarantees any chunk that fits provider 1
  will also fit providers 2 and 3, so a 413 on fallthrough is essentially
  impossible — only a genuine oversized single-chunk edge case triggers the
  splitting path.
- **One entity per chunk, currently.** For sources with many entities per
  page (e.g. a jobs listing page with 50 postings), the upstream scraper
  should pre-split into one chunk per listing before calling `extract()`
  rather than relying on the LLM to return an array — this keeps the schema
  contract simple and keeps failures isolated to one entity instead of
  invalidating an entire batch.
- **Retries are per-provider, not global**, so a chunk gets
  `max_retries_per_provider × len(providers)` total attempts in the worst
  case — tune `max_retries_per_provider` down for high-volume runs where
  moving to the next tier quickly matters more than milking one provider.
