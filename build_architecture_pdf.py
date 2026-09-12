from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a1a1a"))
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=6)
small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))

doc = SimpleDocTemplate(
    "/home/claude/project/architecture.pdf",
    pagesize=letter,
    topMargin=0.6 * inch,
    bottomMargin=0.6 * inch,
    leftMargin=0.7 * inch,
    rightMargin=0.7 * inch,
)

story = []

story.append(Paragraph("GraphOne / FrontierAtlas — Ingestion Pipeline Architecture", h1))
story.append(Paragraph("AI Engineer Demo Task — Technical Architecture Document", small))
story.append(Spacer(1, 10))

# --- Scale Strategy ---
story.append(Paragraph("1. Scale Strategy: Collecting 500,000+ Records Without Manual Intervention", h2))
story.append(Paragraph(
    "The pipeline is split into three horizontally-independent stages -- fetch, extract, resolve -- connected by durable "
    "queues (not direct function calls), so each stage scales on its own axis and a slowdown in one never blocks the others.",
    body,
))
story.append(ListFlowable([
    ListItem(Paragraph(
        "<b>Fetch (I/O-bound):</b> An <b>AdaptiveFetcher</b> (src/scraper/fetcher.py) tries a cheap async HTTP request "
        "first (aiohttp) and only escalates to a real headless browser (Playwright) when the response looks bot-blocked "
        "(403/503, or a Cloudflare/Datadome challenge marker in the body). Because &gt;90% of directory/listing pages are "
        "plain HTML, this keeps the median cost-per-page low, and horizontal scale is just 'run more worker processes/pods "
        "against more URL-queue partitions' -- no code changes, only replica count.", body)),
    ListItem(Paragraph(
        "<b>Extract (compute-bound, rate-limited by vendor):</b> The <b>LLMOrchestrator</b> (src/llm/orchestrator.py) "
        "processes chunks with bounded concurrency (asyncio.Semaphore) per worker; scaling to 500k records means running "
        "more worker replicas, each with its own concurrency budget, against a shared work queue -- again no code change. "
        "The 3-tier fallback (Gemini Flash -> Groq Llama 3 -> DeepSeek) means the effective extraction throughput is the "
        "SUM of all three providers' rate limits, not the minimum of one.", body)),
    ListItem(Paragraph(
        "<b>Resolve (CPU-bound, embarrassingly parallel):</b> Entity resolution is a pure function of (raw_name, current "
        "canonical index) with no external calls, so it scales linearly with CPU cores. The only shared-state concern is "
        "the canonical index itself when new entities are registered concurrently -- addressed via a single-writer queue "
        "(see Freshness Tracking below for the same underlying pattern).", body)),
], bulletType="bullet", start="circle"))
story.append(Paragraph(
    "Concretely: a work-queue-per-vertical (Startups, Products, Papers, Jobs, News) fed by seed-URL crawlers (directory "
    "pagination for startups/products, arXiv/HF listing APIs for papers, RSS/sitemap polling for news, board-specific "
    "pagination for jobs), consumed by a pool of fetch workers, whose output feeds an extraction queue consumed by a pool "
    "of LLM workers, whose output feeds a resolution+load queue. Each pool's replica count is an infrastructure dial, "
    "not a code change -- this is the literal mechanism behind 'scale to 500k with infra, not code.'",
    body,
))

# --- 413/429 ---
story.append(Paragraph("2. Handling 413s and 429s Across Thousands of Concurrent Extractions", h2))
story.append(Paragraph("<b>413 Payload Too Large (proactive + reactive):</b>", body))
story.append(Paragraph(
    "Proactively, src/llm/chunker.py splits any scraped text on paragraph/heading boundaries to stay under "
    "max_tokens_per_chunk, sized to the TIGHTEST provider in the fallback chain -- so a chunk that clears tier 1 is "
    "guaranteed to clear tiers 2 and 3 as well, making a 413-on-fallthrough essentially impossible. Reactively, if a "
    "413 still occurs (e.g. a single oversized paragraph), the orchestrator halves the chunk and retries the SAME "
    "provider first (cheaper than switching tiers), recursing up to max_chunk_splits times before falling through.",
    body,
))
story.append(Paragraph("<b>429 Rate Limited (per-provider backoff, then fallthrough):</b>", body))
story.append(Paragraph(
    "Each provider gets up to max_retries_per_provider attempts with exponential backoff plus jitter "
    "(base * 2^attempt + random jitter, capped at max_backoff_seconds) before the orchestrator falls through to the "
    "next tier in the chain. Backoff is scoped per-provider-per-chunk, not global, so one rate-limited provider does not "
    "stall unrelated chunks being processed by other workers. At fleet scale, each worker additionally tracks a rolling "
    "estimate of remaining quota per provider (from response headers where available) and proactively throttles its own "
    "concurrency before hitting 429s at all -- backoff-after-429 is the safety net, not the primary control.",
    body,
))

# --- Freshness ---
story.append(Paragraph("3. Freshness Tracking Across Distributed Crawler Nodes", h2))
story.append(Paragraph(
    "Deduplication is anchored on a canonical identity per vertical, not the crawl timestamp: (source_domain, "
    "canonical_article_url) for news, (job_board, requisition_id) for jobs, arXiv ID for papers. Every worker checks a "
    "shared, centrally-addressable key-value store (Redis, or a Postgres table with a UNIQUE constraint used as a "
    "de-dup gate) BEFORE enqueuing extraction work for a URL -- an atomic SETNX-style check-and-set means two crawler "
    "nodes racing on the same URL only result in one of them proceeding, no matter how many nodes are running.",
    body,
))
story.append(Paragraph(
    "For date normalization: absolute dates in meta tags are parsed and stored in UTC ISO-8601 directly. Relative "
    "dates ('2 hours ago') are resolved against the HTTP response's Date header (not local wall-clock, which drifts "
    "across nodes) at fetch time. Where a source exposes neither, we apply the heuristic: a URL/requisition ID is "
    "'new' if and only if it is absent from the de-dup store at check time -- meaning the FIRST time any node observes "
    "it, it is fresh by definition, and it never re-qualifies as fresh on a later crawl even if the page content changes, "
    "unless the content hash changes materially (re-published/updated article), which is tracked separately as an "
    "'updated_at' rather than a new-record event.",
    body,
))

# --- Storage ---
story.append(Paragraph("4. Storage Strategy", h2))
t = Table(
    [
        ["Layer", "Choice", "Why"],
        ["Primary record store", "PostgreSQL", "Strong schema + JSONB for the nested content.* fields gives us both "
         "relational integrity (unique constraints for dedup) and schema flexibility per entity type, without needing "
         "a document DB. Battle-tested at the write volumes this pipeline produces."],
        ["Queueing", "Redis Streams / SQS", "Durable work queues between fetch -> extract -> resolve stages; Redis "
         "also doubles as the freshness dedup store (fast SETNX checks)."],
        ["Relationship / graph layer", "Neo4j (or Postgres + pg_graph extension at smaller scale)", "The core product "
         "is an Intelligence GRAPH: Startup -[BUILDS]-> Product, Startup -[EMPLOYS_VIA]-> Job, Paper "
         "-[AUTHORED_BY/CITES]-> Startup/Paper. These are natively multi-hop graph queries ('find all papers "
         "connected to startups that posted a job in the last week') that are awkward as repeated SQL joins but "
         "natural in Cypher."],
        ["Vector layer", "pgvector (colocated with Postgres) or a dedicated vector DB (Pinecone/Qdrant) once scale "
         "demands it", "Embeddings of paper abstracts / product descriptions power semantic search and duplicate-"
         "candidate detection (a fuzzy-match miss can still be caught via embedding similarity above a threshold, "
         "feeding back into entity resolution as a second-opinion signal)."],
    ],
    colWidths=[1.3 * inch, 1.7 * inch, 3.6 * inch],
)
t.setStyle(TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(t)
story.append(Spacer(1, 8))
story.append(Paragraph(
    "Rationale for splitting graph and vector layers rather than picking one: relationship traversal (graph) and "
    "semantic similarity (vector) answer fundamentally different questions, and forcing one engine to do both "
    "(e.g. a pure vector DB simulating relationships via metadata filters) degrades either the traversal performance "
    "or the recall quality. Postgres remains the system of record throughout -- both Neo4j and the vector store are "
    "kept in sync via change-data-capture from Postgres (Debezium or a simple outbox-table pattern), so there is a "
    "single source of truth and no risk of the graph/vector views drifting from the canonical data.",
    body,
))

story.append(Spacer(1, 10))
story.append(Paragraph(
    "Companion engineering artifacts: src/llm/ (multi-tier extraction, tested), src/entity_resolution/ (canonicalization, "
    "tested), src/scraper/ (adaptive fetcher + GitHub star tracking). See README.md for setup and the demo-scale data "
    "pull methodology.",
    small,
))

doc.build(story)
print("architecture.pdf built")
