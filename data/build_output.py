"""
Build the 6 GraphOne / FrontierAtlas deliverable CSV tabs.

This script builds the currently verified demo dataset from the
data/real_*.py modules.

Important:
- It does not fabricate records.
- It preserves source URLs and available metadata.
- Jobs and news are passed through the 24-hour freshness gate.
- The live scraper + LLM orchestrator are separate pipeline components
  and are covered by their automated tests.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.entity_resolution import EntityResolver
from src.utils.freshness import normalize_date, is_fresh

from data.real_research_papers import RESEARCH_PAPERS
from data.real_startups import STARTUPS
from data.real_news import NEWS_ITEMS
from data.real_jobs import JOBS


OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

NOW_DT = datetime.now(timezone.utc)
NOW = NOW_DT.isoformat()

resolver = EntityResolver()


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    """Write records to a CSV file."""
    path = OUTPUT_DIR / filename

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows):>4} rows -> {path}")


def build_startups_and_products():
    """Build startup and product records from the verified startup dataset."""
    startup_rows = []
    product_rows = []

    for s in STARTUPS:
        resolution = resolver.resolve(s["entityName"])

        startup_rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "STARTUP",
                "source.name": "Y Combinator Startup Directory",
                "source.url": s["source_url"],
                "content.entityName": resolution.canonical_name,
                "content.data.employeeCount": s["employeeCount"],
                "collectedAt": NOW,
            }
        )

        product_rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "PRODUCT",
                "source.name": "Y Combinator Startup Directory",
                "source.url": s["source_url"],
                "content.startupName": resolution.canonical_name,
                "content.pricingModel": "",
                "content.description": s["description"],
                "collectedAt": NOW,
            }
        )

    return startup_rows, product_rows


def build_research_papers():
    """Build research-paper records while preserving verified metadata."""
    rows = []

    for p in RESEARCH_PAPERS:
        rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "RESEARCH_PAPER",
                "source.name": p["source_name"],
                "source.url": p["paper_url"],
                "content.title": p["title"],
                "content.authors": ", ".join(p.get("authors", [])),
                "content.paper_url": p["paper_url"],
                "content.github_url": p.get("github_url"),
                "content.github_stars": p.get("github_stars"),
                "content.published_date": p.get("published_date"),
                "collectedAt": NOW,
            }
        )

    return rows


def build_jobs():
    """
    Build only jobs that are fresh within the required 24-hour window.

    Unknown or stale dates are excluded rather than guessed.
    """
    rows = []
    skipped = 0

    for j in JOBS:
        parsed = normalize_date(j.get("date"), reference_time=NOW_DT)

        if not is_fresh(
            parsed,
            reference_time=NOW_DT,
            window_hours=24,
        ):
            skipped += 1
            continue

        resolution = resolver.resolve(j["company"])

        rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "JOB",
                "source.name": j["source_name"],
                "source.url": j["source_url"],
                "content.company": resolution.canonical_name,
                "content.title": j["title"],
                "content.date": j["date"],
                "content.is_remote": j["is_remote"],
                "content.role_family": j["role_family"],
                "collectedAt": NOW,
            }
        )

    print(f"fresh jobs included: {len(rows)}")
    print(f"stale/unknown jobs skipped: {skipped}")

    return rows


def build_news():
    """
    Build only news items that are fresh within the required 24-hour window.

    Unknown or stale dates are excluded rather than guessed.
    """
    rows = []
    skipped = 0

    for n in NEWS_ITEMS:
        parsed = normalize_date(
            n.get("published_date"),
            reference_time=NOW_DT,
        )

        if not is_fresh(
            parsed,
            reference_time=NOW_DT,
            window_hours=24,
        ):
            skipped += 1
            continue

        rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "NEWS",
                "source.name": n["source_name"],
                "source.url": n["source_url"],
                "content.title": n["title"],
                "content.published_date": n["published_date"],
                "content.excerpt": n["content_excerpt"],
                "collectedAt": NOW,
            }
        )

    print(f"fresh news included: {len(rows)}")
    print(f"stale/unknown news skipped: {skipped}")

    return rows


def main():
    startup_rows, product_rows = build_startups_and_products()

    write_csv(
        "startups.csv",
        startup_rows,
        [
            "schemaVersion",
            "recordType",
            "source.name",
            "source.url",
            "content.entityName",
            "content.data.employeeCount",
            "collectedAt",
        ],
    )

    write_csv(
        "products.csv",
        product_rows,
        [
            "schemaVersion",
            "recordType",
            "source.name",
            "source.url",
            "content.startupName",
            "content.pricingModel",
            "content.description",
            "collectedAt",
        ],
    )

    write_csv(
        "research_papers.csv",
        build_research_papers(),
        [
            "schemaVersion",
            "recordType",
            "source.name",
            "source.url",
            "content.title",
            "content.authors",
            "content.paper_url",
            "content.github_url",
            "content.github_stars",
            "content.published_date",
            "collectedAt",
        ],
    )

    write_csv(
        "jobs.csv",
        build_jobs(),
        [
            "schemaVersion",
            "recordType",
            "source.name",
            "source.url",
            "content.company",
            "content.title",
            "content.date",
            "content.is_remote",
            "content.role_family",
            "collectedAt",
        ],
    )

    write_csv(
        "news.csv",
        build_news(),
        [
            "schemaVersion",
            "recordType",
            "source.name",
            "source.url",
            "content.title",
            "content.published_date",
            "content.excerpt",
            "collectedAt",
        ],
    )

    write_csv(
        "entity_mapping_log.csv",
        resolver.export_mapping_log_rows(),
        [
            "raw_name",
            "canonical_name",
            "method",
            "confidence",
        ],
    )


if __name__ == "__main__":
    main()