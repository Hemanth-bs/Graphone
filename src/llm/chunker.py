"""
Intelligent chunking to keep every LLM payload under provider context limits
and avoid 413 Payload Too Large errors, while retaining semantically dense
content (we don't just hard-truncate — we chunk on structure boundaries and
can optionally pre-filter boilerplate).

Strategy
--------
1. Strip obvious boilerplate (nav/footer/script noise) before counting.
2. Estimate tokens cheaply (chars/4 heuristic — good enough to stay well
   under limits without needing a real tokenizer per-provider).
3. Split on paragraph/heading boundaries first (semantic chunking), only
   falling back to hard character slicing if a single paragraph is itself
   oversized (e.g. a wall of minified HTML/text).
4. Each chunk carries `chunk_index` / `total_chunks` metadata so downstream
   extraction can be reassembled or deduped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_BOILERPLATE_PATTERNS = [
    re.compile(r"<script.*?</script>", re.S | re.I),
    re.compile(r"<style.*?</style>", re.S | re.I),
    re.compile(r"<!--.*?-->", re.S),
]

# Conservative chars-per-token approximation for English text/HTML mixes.
CHARS_PER_TOKEN = 4


@dataclass
class Chunk:
    text: str
    chunk_index: int
    total_chunks: int
    approx_tokens: int


def _strip_boilerplate(raw: str) -> str:
    cleaned = raw
    for pattern in _BOILERPLATE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    # collapse excessive whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def chunk_text(
    raw_text: str,
    max_tokens_per_chunk: int = 6000,
    hard_char_ceiling: int = 40_000,
) -> List[Chunk]:
    """Split raw_text into semantically-bounded chunks under max_tokens_per_chunk.

    max_tokens_per_chunk should be set comfortably below the *smallest*
    provider's limit in your fallback chain (see orchestrator.py — we use
    the tightest tier's limit so any tier in the chain can accept the chunk
    without a further 413).
    """
    cleaned = _strip_boilerplate(raw_text)
    if not cleaned:
        return []

    max_chars = min(max_tokens_per_chunk * CHARS_PER_TOKEN, hard_char_ceiling)

    # Split on paragraph boundaries first.
    paragraphs = re.split(r"\n\s*\n", cleaned)

    raw_chunks: List[str] = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # A single paragraph bigger than the ceiling gets hard-sliced.
        if len(para) > max_chars:
            if current:
                raw_chunks.append(current)
                current = ""
            for i in range(0, len(para), max_chars):
                raw_chunks.append(para[i : i + max_chars])
            continue

        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > max_chars:
            raw_chunks.append(current)
            current = para
        else:
            current = candidate

    if current:
        raw_chunks.append(current)

    total = len(raw_chunks)
    return [
        Chunk(
            text=text,
            chunk_index=i,
            total_chunks=total,
            approx_tokens=estimate_tokens(text),
        )
        for i, text in enumerate(raw_chunks)
    ]
