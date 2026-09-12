"""
End-to-end pipeline run (demo scale) producing the 6 deliverable tabs.

This script deliberately uses REAL, already-collected data (see data/real_*.py
-- each traced to a live source fetched/searched on 2026-09-12) rather than
calling the LLM orchestrator against live scrapes, for two reasons:

  1. This sandbox's outbound network is restricted to package registries
     (pypi/npm/github) for the bash/aiohttp path -- it cannot reach arXiv,
     news sites, or job boards directly, so `src/scraper` cannot be executed
     live here even though it is complete and unit-testable.
  2. No LLM provider API keys (Gemini/Groq/DeepSeek) are configured in this
     environment, so `src/llm/orchestrator.py` has no live tier to call.

What IS real: every row below traces to an actual fetched/searched URL from
this session -- GitHub stars were pulled live from api.github.com, and
startup/job/news data was extracted by hand from real fetched pages (i.e.
this script performs the "Phase III extraction" step directly, the same
transformation `orchestrator.py` automates when wired to a real page +
API keys). Wire this script's data loading to `src/scraper` + `src/llm` in
place of the `data/real_*.py` imports to go from demo-scale to production.

Run with: python -m data.build_output
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.entity_resolution import EntityResolver
from data.real_research_papers import RESEARCH_PAPERS
from data.real_startups import STARTUPS
from data.real_news import NEWS_ITEMS
from data.real_jobs import JOBS

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

NOW = datetime.utcnow().isoformat()
resolver = EntityResolver()


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"wrote {len(rows):>4} rows -> {path}")


def build_startups_and_products():
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
        # Every YC company profile also describes a flagship product; we
        # derive one PRODUCT record per STARTUP record here. pricingModel is
        # left blank rather than guessed, since YC profiles don't state it.
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
    rows = []
    for p in RESEARCH_PAPERS:
        rows.append(
            {
                "schemaVersion": "1.0",
                "recordType": "RESEARCH_PAPER",
                "source.name": p["source_name"],
                "source.url": p["source_url"],
                "content.title": p["title"],
                "content.authors": "",
                "content.paper_url": p["paper_url"],
                "content.github_url": p["github_url"],
                "content.github_stars": p["github_stars"],
                "content.published_date": p["published_date"],
                "collectedAt": NOW,
            }
        )
    return rows


def build_jobs():
    rows = []
    for j in JOBS:
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
    return rows


def build_news():
    rows = []
    for n in NEWS_ITEMS:
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
    return rows


def main():
    startup_rows, product_rows = build_startups_and_products()
    write_csv(
        "startups.csv",
        startup_rows,
        ["schemaVersion", "recordType", "source.name", "source.url", "content.entityName", "content.data.employeeCount", "collectedAt"],
    )
    write_csv(
        "products.csv",
        product_rows,
        ["schemaVersion", "recordType", "source.name", "source.url", "content.startupName", "content.pricingModel", "content.description", "collectedAt"],
    )
    write_csv(
        "research_papers.csv",
        build_research_papers(),
        ["schemaVersion", "recordType", "source.name", "source.url", "content.title", "content.authors", "content.paper_url", "content.github_url", "content.github_stars", "content.published_date", "collectedAt"],
    )
    write_csv(
        "jobs.csv",
        build_jobs(),
        ["schemaVersion", "recordType", "source.name", "source.url", "content.company", "content.title", "content.date", "content.is_remote", "content.role_family", "collectedAt"],
    )
    write_csv(
        "news.csv",
        build_news(),
        ["schemaVersion", "recordType", "source.name", "source.url", "content.title", "content.published_date", "content.excerpt", "collectedAt"],
    )
    write_csv(
        "entity_mapping_log.csv",
        resolver.export_mapping_log_rows(),
        ["raw_name", "canonical_name", "method", "confidence"],
    )


if __name__ == "__main__":
    main()
