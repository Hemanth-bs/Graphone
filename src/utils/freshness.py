"""
Freshness / date-normalization utility (Phase II support, spec section 15).

Handles the messy reality of scraped dates:
  - absolute ISO timestamps
  - relative strings ("2 hours ago", "Yesterday", "Today", "30 minutes ago")
  - short absolute strings missing a year ("Sep 12")
  - missing/unparseable dates

Everything is timezone-aware UTC. We never use datetime.utcnow() (naive) --
see orchestrator.py / schemas.py for the same fix applied there.

A record's freshness is only ever claimed "confident" when we had an
absolute timestamp or an unambiguous relative offset from a known
reference/crawl time. Anything else is marked with a lower confidence and
an explicit reason, per the "do not falsely claim exact freshness" rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

try:
    from dateutil import parser as _dateutil_parser  # type: ignore
except ImportError:  # pragma: no cover - exercised only if dateutil absent
    _dateutil_parser = None


class DateConfidence(str, Enum):
    EXACT = "exact"              # absolute timestamp parsed directly
    RELATIVE_EXACT = "relative_exact"   # "2 hours ago" relative to a known reference time
    HEURISTIC = "heuristic"      # partial info (e.g. "Sep 12", no year) -- inferred
    UNKNOWN = "unknown"          # could not parse at all


@dataclass
class ParsedDate:
    value: Optional[datetime]     # tz-aware UTC, or None if unparseable
    confidence: DateConfidence
    reason: str


_RELATIVE_UNITS = {
    "second": 1,
    "minute": 60,
    "min": 60,
    "hour": 3600,
    "hr": 3600,
    "day": 86400,
    "week": 604800,
}

_RELATIVE_RE = re.compile(
    r"^\s*(?P<num>\d+)\s*(?P<unit>second|minute|min|hour|hr|day|week)s?\s+ago\s*$",
    re.IGNORECASE,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_date(raw: Optional[str], reference_time: Optional[datetime] = None) -> ParsedDate:
    """Normalize a raw date string into a tz-aware UTC ParsedDate.

    `reference_time` is the crawl/collection timestamp used to resolve
    relative expressions ("2 hours ago", "Today", "Yesterday"). It defaults
    to now(UTC) but callers should pass the actual collection timestamp for
    reproducible tests / auditability.
    """
    reference_time = _ensure_utc(reference_time or datetime.now(timezone.utc))

    if raw is None or not str(raw).strip():
        return ParsedDate(None, DateConfidence.UNKNOWN, "missing_date_string")

    text = str(raw).strip()
    lowered = text.lower()

    if lowered in ("today",):
        return ParsedDate(reference_time, DateConfidence.RELATIVE_EXACT, "relative:today")

    if lowered in ("yesterday",):
        return ParsedDate(
            reference_time - timedelta(days=1),
            DateConfidence.RELATIVE_EXACT,
            "relative:yesterday",
        )

    m = _RELATIVE_RE.match(lowered)
    if m:
        seconds = int(m.group("num")) * _RELATIVE_UNITS[m.group("unit").lower()]
        return ParsedDate(
            reference_time - timedelta(seconds=seconds),
            DateConfidence.RELATIVE_EXACT,
            f"relative:{m.group('num')}_{m.group('unit')}_ago",
        )

    # Absolute parse attempt (handles ISO 8601, RFC 2822, "Sep 12 2026", etc.)
    if _dateutil_parser is not None:
        try:
            parsed = _dateutil_parser.parse(text, default=reference_time)
        except (ValueError, OverflowError):
            parsed = None
    else:
        parsed = None

    if parsed is not None:
        parsed = _ensure_utc(parsed)
        # Detect "no year in the source string" -> heuristic, not exact.
        # dateutil silently fills in the year from `default` in that case;
        # we flag it rather than claim an exact publish date, per spec:
        # "Do not derive an exact publication date from only YYYY-MM info."
        has_year = bool(re.search(r"\b\d{4}\b", text))
        if has_year:
            return ParsedDate(parsed, DateConfidence.EXACT, "absolute_parsed")
        return ParsedDate(
            parsed, DateConfidence.HEURISTIC, "absolute_parsed_year_inferred_from_reference_time"
        )

    return ParsedDate(None, DateConfidence.UNKNOWN, f"unparseable:{text!r}")


def is_fresh(parsed: ParsedDate, reference_time: Optional[datetime] = None, window_hours: int = 24) -> bool:
    """True only if parsed.value is known and within the freshness window.

    Records with UNKNOWN confidence are never considered fresh -- we do not
    default missing dates to "now" (that would fabricate freshness).
    """
    if parsed.value is None or parsed.confidence == DateConfidence.UNKNOWN:
        return False
    reference_time = _ensure_utc(reference_time or datetime.now(timezone.utc))
    window_start = reference_time - timedelta(hours=window_hours)
    return window_start <= parsed.value <= reference_time
