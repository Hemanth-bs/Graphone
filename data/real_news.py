"""
Real AI news items, each traced to a real source URL found via live web search
on 2026-09-12. Content is paraphrased in our own words (not reproduced
verbatim) per source-attribution and copyright practice. Dates reflect each
item's actual publication date as reported by the source.

Freshness note: this is a point-in-time demo pull via web_search rather than
a running crawler, so items span roughly Sept 9-12, 2026 rather than a strict
rolling 24h window. The production crawler (src/scraper) enforces the strict
24h freshness filter continuously; see architecture.pdf, "Freshness Tracking".
"""

NEWS_ITEMS = [
    {
        "title": "Anthropic reports escalating distillation attacks from China-based AI labs",
        "source_name": "TechCrunch (via AI News aggregation)",
        "source_url": "https://www.cryptointegrat.com/p/ai-news-september-11-2026",
        "published_date": "2026-09-11T00:00:00",
        "content_excerpt": "Anthropic published a report describing sustained attempts by China-based AI companies, including Alibaba, Moonshot AI, and DeepSeek, to distill its models' capabilities, with the pattern intensifying as competition in frontier AI has increased.",
    },
    {
        "title": "OpenAI opens public beta of its Agents API",
        "source_name": "AI Weekly",
        "source_url": "https://aiweekly.co/ai-news-today",
        "published_date": "2026-09-10T00:00:00",
        "content_excerpt": "OpenAI made its Agents API publicly available, exposing the managed Codex harness that handles sessions, orchestration, context compaction, and recovery, leaving developers to supply tools and choose execution environments.",
    },
    {
        "title": "Oracle cloud infrastructure revenue jumps 121% on AI demand",
        "source_name": "AI Weekly",
        "source_url": "https://aiweekly.co/ai-news-today",
        "published_date": "2026-09-10T00:00:00",
        "content_excerpt": "Oracle reported first-quarter fiscal 2027 revenue of $19.3B, up 30% year over year, with cloud infrastructure revenue up 121% to $7.4B; the company added over $30B in AI cloud contracts and grew its remaining performance obligations to $664B.",
    },
    {
        "title": "US AI industry framed as an industrial buildout, not just a model race",
        "source_name": "HIPTHER",
        "source_url": "https://hipther.com/news/2026/09/11/129962/ai-dispatch-daily-trends-and-innovations-september-11-2026-chinese-ai-labs-gemini-for-windows-gpt-li",
        "published_date": "2026-09-11T00:00:00",
        "content_excerpt": "Coverage on Sept 11 framed the AI industry increasingly around infrastructure control -- compute, data, and operational boundaries -- citing OpenAI's optical-manufacturing expansion with Frontline Defenders as a sign the boom is spreading into physical industry.",
    },
    {
        "title": "Microsoft plans data-center capacity growth from 12GW to 38GW+ by 2032",
        "source_name": "AI Weekly (citing Bloomberg)",
        "source_url": "https://aiweekly.co/ai-news-today",
        "published_date": "2026-09-10T00:00:00",
        "content_excerpt": "Microsoft laid out plans to grow AI-specific data-center capacity roughly threefold by 2032, according to reporting cited in AI Weekly's daily roundup.",
    },
    {
        "title": "Agentic flooding: cheap LLM text linked to surges in public complaints",
        "source_name": "Tech Startups",
        "source_url": "https://techstartups.com/2026/09/11/top-tech-news-today-september-11-2026-anthropic-deepseek-google-pentagon-oracle-spacex-more/",
        "published_date": "2026-09-11T00:00:00",
        "content_excerpt": "A researcher documented dozens of cases across multiple countries where inexpensively generated LLM text appears to be driving increases in applications and complaints filed with public agencies, including a large jump in a UK housing ombudsman's complaint volume.",
    },
    {
        "title": "ChatGPT gains native Dropbox, Box, and SharePoint integration",
        "source_name": "Crypto Integrated AI roundup",
        "source_url": "https://www.cryptointegrat.com/p/ai-news-september-11-2026",
        "published_date": "2026-09-10T00:00:00",
        "content_excerpt": "OpenAI began rolling out native integrations for Dropbox, Box, and SharePoint inside the ChatGPT Library for paid ChatGPT and ChatGPT Work users, alongside the ability to open Google Drive files without switching tabs.",
    },
]
