"""
Deterministic entity resolution engine (Phase IV).

Pipeline, in order (cheapest/most-precise first):
  1. Exact match (case/whitespace-normalized) against canonical name or any
     known alias.
  2. Normalized match after stripping legal suffixes ("Inc.", "PBC", "Ltd",
     "Technologies", punctuation, etc.) — catches "OpenAI, Inc." vs "OpenAI".
  3. Fuzzy match (token-sort ratio via rapidfuzz) against the alias index,
     accepted only above a high similarity threshold to avoid false merges.
  4. If nothing clears the threshold, the entity is treated as genuinely
     novel and is auto-registered as its own new canonical entry (with the
     raw string as its canonical name) rather than silently dropped or
     forced into an unrelated bucket — this keeps recall high without
     corrupting existing canonical clusters.

Every resolution — matched or newly registered — is logged to build the
"Entity Mapping Log" deliverable (raw string -> canonical name -> method).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rapidfuzz import fuzz

from .seed_data import CANONICAL_STARTUPS

# NOTE: "ai"/"a.i." was previously stripped as a "legal suffix" alongside
# things like "inc"/"ltd". That's wrong: "AI" is very often part of the
# actual brand identity (Together AI, Cohere, Runway ML's "AI" variants,
# etc.), not a corporate-form suffix like "Inc." is. Stripping it caused
# false merges -- e.g. "Together AI" and an unrelated "Together" (a
# different company) both normalized down to "together" and were treated
# as the same canonical entity. Legal-form suffixes (Inc/LLC/Ltd/Corp/...)
# are safe to strip because they never carry brand meaning; "AI" does, so
# it's excluded here and left for the fuzzy-match tier (with its high
# threshold) to handle the genuine near-duplicates.
_LEGAL_SUFFIXES = re.compile(
    r"\b(inc|inc\.|llc|llc\.|ltd|ltd\.|pbc|corp|corp\.|corporation|"
    r"technologies|technology|labs|lab|systems|solutions|company|co\.|gmbh|"
    r"b\.v\.)\b",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s]")


def _normalize(name: str) -> str:
    n = name.lower().strip()
    n = _PUNCT.sub(" ", n)
    n = _LEGAL_SUFFIXES.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


@dataclass
class ResolutionRecord:
    raw_name: str
    canonical_name: str
    method: str          # "exact" | "normalized" | "fuzzy" | "new_entity"
    confidence: float    # 0.0 - 1.0


@dataclass
class EntityResolver:
    canonical_map: Dict[str, List[str]] = field(default_factory=lambda: dict(CANONICAL_STARTUPS))
    fuzzy_threshold: float = 90.0  # rapidfuzz token_sort_ratio, 0-100

    def __post_init__(self):
        self._alias_index: Dict[str, str] = {}          # normalized alias -> canonical
        self._exact_index: Dict[str, str] = {}           # normalized exact -> canonical
        self._rebuild_index()
        self.mapping_log: List[ResolutionRecord] = []

    def _rebuild_index(self) -> None:
        self._alias_index.clear()
        self._exact_index.clear()
        for canonical, aliases in self.canonical_map.items():
            self._exact_index[canonical.lower().strip()] = canonical
            self._alias_index[_normalize(canonical)] = canonical
            for alias in aliases:
                self._exact_index[alias.lower().strip()] = canonical
                self._alias_index[_normalize(alias)] = canonical

    def resolve(self, raw_name: str) -> ResolutionRecord:
        if not raw_name or not raw_name.strip():
            record = ResolutionRecord(raw_name, raw_name, "skipped_empty", 0.0)
            self.mapping_log.append(record)
            return record

        exact_key = raw_name.lower().strip()
        if exact_key in self._exact_index:
            record = ResolutionRecord(raw_name, self._exact_index[exact_key], "exact", 1.0)
            self.mapping_log.append(record)
            return record

        norm_key = _normalize(raw_name)
        if norm_key in self._alias_index:
            record = ResolutionRecord(raw_name, self._alias_index[norm_key], "normalized", 0.97)
            self.mapping_log.append(record)
            return record

        best_canonical: Optional[str] = None
        best_score = 0.0
        for alias_norm, canonical in self._alias_index.items():
            score = fuzz.token_sort_ratio(norm_key, alias_norm)
            if score > best_score:
                best_score = score
                best_canonical = canonical

        if best_canonical and best_score >= self.fuzzy_threshold:
            record = ResolutionRecord(raw_name, best_canonical, "fuzzy", best_score / 100.0)
            self.mapping_log.append(record)
            return record

        # Genuinely new entity — register it so future variants of THIS name
        # also resolve correctly within the same run.
        canonical_new = raw_name.strip()
        self.canonical_map[canonical_new] = []
        self._exact_index[canonical_new.lower().strip()] = canonical_new
        self._alias_index[_normalize(canonical_new)] = canonical_new
        record = ResolutionRecord(raw_name, canonical_new, "new_entity", 1.0)
        self.mapping_log.append(record)
        return record

    def resolve_batch(self, raw_names: List[str]) -> List[ResolutionRecord]:
        return [self.resolve(n) for n in raw_names]

    def export_mapping_log_rows(self) -> List[dict]:
        return [
            {
                "raw_name": r.raw_name,
                "canonical_name": r.canonical_name,
                "method": r.method,
                "confidence": round(r.confidence, 3),
            }
            for r in self.mapping_log
        ]
