from datetime import datetime, timedelta, timezone

from src.utils.freshness import DateConfidence, is_fresh, normalize_date

REF = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)


def test_exact_iso_timestamp():
    parsed = normalize_date("2026-09-12T10:00:00Z", reference_time=REF)
    assert parsed.confidence == DateConfidence.EXACT
    assert parsed.value == datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)


def test_relative_hours_ago():
    parsed = normalize_date("2 hours ago", reference_time=REF)
    assert parsed.confidence == DateConfidence.RELATIVE_EXACT
    assert parsed.value == REF - timedelta(hours=2)


def test_relative_minutes_ago():
    parsed = normalize_date("30 minutes ago", reference_time=REF)
    assert parsed.value == REF - timedelta(minutes=30)


def test_today():
    parsed = normalize_date("Today", reference_time=REF)
    assert parsed.value == REF


def test_yesterday():
    parsed = normalize_date("Yesterday", reference_time=REF)
    assert parsed.value == REF - timedelta(days=1)


def test_missing_date_is_unknown_not_now():
    parsed = normalize_date(None, reference_time=REF)
    assert parsed.confidence == DateConfidence.UNKNOWN
    assert parsed.value is None


def test_year_missing_from_string_is_heuristic_not_exact():
    parsed = normalize_date("Sep 12", reference_time=REF)
    assert parsed.confidence == DateConfidence.HEURISTIC


def test_freshness_within_24h():
    parsed = normalize_date("5 hours ago", reference_time=REF)
    assert is_fresh(parsed, reference_time=REF, window_hours=24) is True


def test_freshness_exactly_24h_boundary_is_fresh():
    parsed = normalize_date("2026-09-11T12:00:00Z", reference_time=REF)
    assert is_fresh(parsed, reference_time=REF, window_hours=24) is True


def test_freshness_over_24h_is_stale():
    parsed = normalize_date("2026-09-10T00:00:00Z", reference_time=REF)
    assert is_fresh(parsed, reference_time=REF, window_hours=24) is False


def test_unknown_date_never_counts_as_fresh():
    parsed = normalize_date("garbled nonsense !!", reference_time=REF)
    assert is_fresh(parsed, reference_time=REF) is False
