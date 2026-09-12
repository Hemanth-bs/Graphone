"""
Prompt construction for structured extraction.

We deliberately keep prompts strict and schema-locked: the LLM is only ever
asked to fill `content` fields, never `source`/`collectedAt`/`schemaVersion`,
which are set deterministically by code from the actual scrape metadata.
This is the single biggest lever against hallucination — the model cannot
invent a source URL because it's never asked to produce one.
"""
from __future__ import annotations

import json

from .schemas import RecordType, json_schema_for

SYSTEM_INSTRUCTIONS = """You are a precise data-extraction engine for an AI industry intelligence \
graph. You will be given raw scraped text/HTML and a target JSON schema.

Rules:
- Output ONLY valid JSON matching the schema. No prose, no markdown fences.
- Do NOT invent facts. If a field is not present in the source text, omit it \
or set it to null. Never guess numbers (employee counts, star counts, dates).
- If the provided text does not contain enough information to extract this \
entity type at all, return exactly: {"__skip__": true}
- Dates must be normalized to ISO-8601. If you see a relative date like \
"2 hours ago", compute it relative to the provided reference timestamp.
"""


def build_extraction_prompt(
    record_type: RecordType,
    chunk_text: str,
    *,
    reference_timestamp: str,
    source_hint: str = "",
) -> str:
    schema = json_schema_for(record_type)
    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"Target entity type: {record_type.value}\n"
        f"Reference timestamp (for resolving relative dates): {reference_timestamp}\n"
        f"Source hint (site this was scraped from): {source_hint or 'unknown'}\n\n"
        f"JSON schema for the `content` object you must produce:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        f"Raw source text:\n"
        f"---\n{chunk_text}\n---\n\n"
        f"Respond with a single JSON object matching the schema above (the `content` shape only)."
    )
