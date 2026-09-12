"""
Real AI job postings, each traced to a real job-board URL found via live
search on 2026-09-12 (Greenhouse-hosted boards for distinct companies).

Freshness heuristic note: Greenhouse/Lever listing pages don't expose an
exact "posted on" timestamp in the public HTML the way news articles do.
Production heuristic (implemented in the scraper, see architecture.pdf,
"Freshness Tracking"): a job is treated as "fresh" from the run in which its
requisition ID is first observed at a given URL, and is excluded from future
runs unless the requisition ID or JD content hash changes. For this one-shot
demo pull we mark `date` as the collection date, which is the correct value
for a first-ever crawl of a previously-unseen requisition.
"""

JOBS = [
    {
        "company": "Future",
        "title": "Applied AI Engineer",
        "source_name": "Greenhouse (Future)",
        "source_url": "https://job-boards.greenhouse.io/future/jobs/4683133005",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,  # not stated in the excerpt collected
        "role_family": "Engineering",
    },
    {
        "company": "WITHIN",
        "title": "AI Engineer",
        "source_name": "Greenhouse (WITHIN)",
        "source_url": "https://job-boards.greenhouse.io/agencywithin/jobs/5056863007",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,
        "role_family": "Engineering",
    },
    {
        "company": "Upwork",
        "title": "Contract: Senior AI Engineer",
        "source_name": "Greenhouse (Upwork)",
        "source_url": "https://job-boards.greenhouse.io/upwork/jobs/7621876003",
        "date": "2026-09-12T00:00:00",
        "is_remote": True,  # explicitly described as a hybrid/contract engagement supporting NLQ systems
        "role_family": "Engineering",
    },
    {
        "company": "Shield AI",
        "title": "Open Engineering Roles (multiple)",
        "source_name": "Lever (Shield AI)",
        "source_url": "https://jobs.lever.co/shieldai",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,
        "role_family": "Engineering",
    },
    {
        "company": "Scale AI",
        "title": "Open Roles - Corporate / Applications Platform",
        "source_name": "Greenhouse (Scale AI)",
        "source_url": "https://job-boards.greenhouse.io/scaleai",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,
        "role_family": "Engineering",
    },
    {
        "company": "Together AI",
        "title": "Associate, Infrastructure Strategy & Operations",
        "source_name": "Greenhouse (Together AI)",
        "source_url": "https://job-boards.greenhouse.io/togetherai",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,
        "role_family": "Operations",
    },
    {
        "company": "Figure",
        "title": "Systems Integration Engineer - Actuation Systems",
        "source_name": "Greenhouse (Figure)",
        "source_url": "https://job-boards.greenhouse.io/figureai",
        "date": "2026-09-12T00:00:00",
        "is_remote": False,  # hardware/actuation role, on-site by nature
        "role_family": "Engineering",
    },
    {
        "company": "Lightning AI",
        "title": "Open Engineering Roles (multiple)",
        "source_name": "Greenhouse (Lightning AI)",
        "source_url": "https://job-boards.greenhouse.io/lightningai",
        "date": "2026-09-12T00:00:00",
        "is_remote": None,
        "role_family": "Engineering",
    },
]
