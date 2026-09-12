"""
Real startups scraped from YC's public AI directory
(https://www.ycombinator.com/companies/industry/ai/san-francisco-bay-area,
fetched live on 2026-09-12). Employee counts and descriptions are as
published by YC on each company's page. This is a demo-scale slice (50
companies) of a directory that itself lists 956 -- the scraper/fetcher
module in src/scraper is what would be pointed at the full paginated
directory (and Crunchbase, Product Hunt, etc.) to reach the 1,000+ /
500,000+ targets; see architecture.pdf for the scale-out plan.
"""

# (name, employee_count, description, yc_url_slug)
_RAW = [
    ("Scale AI", 500, "Scale accelerates the development of AI within organizations of any size to deliver critical business insights and operational efficiency, via a data-centric infrastructure platform.", "scale-ai"),
    ("Checkr", 800, "Checkr builds people infrastructure for the future of work, offering faster and fairer background screening for job seekers.", "checkr"),
    ("Mirrors", 2, "Mirrors provides regression testing for AI agents, rebuilding the tools an agent calls from production traces to replay real sessions against changes.", "mirrors"),
    ("Shepherd Robotics", 3, "Shepherd Robotics builds general-purpose robots for skilled physical work in AI infrastructure and advanced manufacturing.", "shepherd-robotics"),
    ("Sona8", 4, "Sona8 is a voice agent that interviews every employee at a company about how their work gets done, building process maps for transformation teams.", "sona8"),
    ("ByteAsk", 2, "ByteAsk is an AI coding agent built for C and C++ that builds, debugs, and tests every change with the real toolchain.", "byteask"),
    ("Frontrunner", 2, "Frontrunner builds agents that research accounts, find prospects, run campaigns, and update CRMs for go-to-market teams.", "frontrunner"),
    ("The Agentic Data Co.", 2, "The Agentic Data Co. designs and collects audio datasets for training speech models.", "the-agentic-data-co"),
    ("SuperRadiant", 3, "SuperRadiant builds general-purpose robotic experimentalists that unite scientific reasoning and physical action for discovery.", "superradiant"),
    ("Dreamscale Labs", 4, "Dreamscale Labs builds a fast cloud inference platform for robotics, offloading physical AI model inference to the cloud.", "dreamscale-labs"),
    ("Hopper", 2, "Hopper lets customers replace models like GPT-4.1 with faster/cheaper open alternatives such as Gemma-4 and qwen3-tts.", "hopper"),
    ("OnePatch", 2, "OnePatch is a forward-deployed AI SRE that instruments services, catches incidents, and drives each one to resolution.", "onepatch"),
    ("Nodus Compute", 2, "Nodus Compute provides an intelligent execution layer for AI workloads.", "nodus-compute"),
    ("Workers IO", 2, "Workers IO verifies systems across millions of interleavings, faults, and timings to find conditions that break software properties.", "workers-io"),
    ("Sentient OS", 2, "Sentient OS runs an on-device LLM nightly on a Mac to understand a user's life context and prepare their day locally.", "sentient-os"),
    ("Studio", 2, "Studio is a simulation lab building live market models of interconnected audience segments from real consumer-behavior data.", "studio"),
    ("OpenTag", 3, "OpenTag is an AI coworker in Slack with full company context that answers questions and keeps a wiki up to date automatically.", "opentag"),
    ("Lantern AI", 4, "Lantern learns what exceptional looks like for a team and runs the full hiring loop from sourcing through offers.", "lantern-ai"),
    ("Callbook AI", 7, "Callbook AI is a collections agency operated by AI that finds, contacts, and negotiates with borrowers on late-stage portfolios.", "callbook-ai"),
    ("Marker", 3, "Marker is a platform for rebuilding enterprises agent-first, delivered by forward-deployed engineers.", "marker"),
    ("antimattr", 2, "antimattr builds a voice-first hardware interface (ring + earphones) for human-agent interaction.", "antimattr"),
    ("Touchy", 3, "Touchy is a personal AI assistant on iPhone that sees, remembers, and takes action across apps via one button press.", "touchy"),
    ("Akon Labs", 2, "Akon Labs (description not published on YC profile at time of collection).", "akon-labs"),
    ("Dream", 2, "Dream makes AI cameras that automatically document vehicle and equipment condition to catch damage teams miss.", "dream"),
    ("Palisade", 1, "Palisade spins up a personal AI sales agent for every visitor to a marketplace website.", "palisade"),
    ("Magma", 1, "Magma enables companies to monetize their agents' traces.", "magma"),
    ("Mochi", 3, "Mochi is an app to watch and create AI-produced anime microdramas with a large creator community.", "mochi"),
    ("DeepReach Inc.", 6, "DeepReach builds a network of wearable stereo capture devices and local data partners to collect real-world physical-AI training data.", "deepreach-inc"),
    ("Moving Atoms", 2, "Moving Atoms trains a video foundation model fine-tuned for physics to let robotics teams train on GPUs instead of manual data.", "moving-atoms"),
    ("Tenor", 3, "Tenor builds infrastructure so domain experts can build, run, and scale AI-native service businesses.", "tenor"),
    ("Simulithic", 2, "Simulithic builds simulations of real users grounded in session data to predict how product changes will perform.", "simulithic"),
    ("Vorelios", 2, "Vorelios builds foundation models that learn physics end-to-end to replace slow, costly engineering simulations.", "vorelios"),
    ("Enact", 2, "Enact creates physical environments to benchmark and hill-climb robotics models on high-value tasks.", "enact"),
    ("Mosaic", 2, "Mosaic gives teams and their coding agents shared memory across sessions for real-time collaborative coding.", "mosaic-inc"),
    ("Erinys", 3, "Erinys provides the technology, intake, and back office needed to launch and scale an AI-native law firm.", "erinys"),
    ("Marengo", 5, "Marengo is an AI-native engineering firm designing data centers in half the time and cost of traditional firms.", "marengo"),
    ("Prodigy Research", 2, "Prodigy is an AI trading research lab that has trained a foundation model for quantitative finance.", "prodigy-research"),
    ("Dawn Industries", 2, "Dawn Industries' VIM product connects to factory equipment to find faults, stage fixes, and recommend corrections in real time.", "dawn-industries"),
    ("Hebbian Robotics", 2, "Hebbian Robotics builds APIs for robotics data teams to verify data quality for model training.", "hebbian-robotics"),
    ("Qlo", 2, "Qlo builds AI agents to run commercial insurance underwriting, automating the operational work around risk decisions.", "qlo"),
    ("Neuromorphic", 3, "Neuromorphic builds robots that work autonomously in existing wet labs alongside human technicians.", "neuromorphic"),
    ("Jcode", 1, "Jcode researches and builds AI agent harnesses, the software layer that wraps an LLM into a working coding agent.", "jcode"),
    ("Forward", 5, "Forward is an AI platform connecting commercial debt advisors with mandate-matching private credit funds.", "useforward"),
    ("Click", 1, "Click builds services inside ChatGPT and Claude that provide external research context beyond built-in web search.", "click"),
    ("Agent FM", 2, "Agent FM is a desktop app giving engineers one group chat to hear and steer their coding agents.", "agent-fm"),
    ("Riften", 5, "Riften is a gateway that routes a company's AI traffic to the lowest-cost model, building toward company-owned private models.", "riften"),
    ("Qokedas", 3, "Qokedas turns real-world signals not found on the internet into training data to make science models better.", "qokedas"),
    ("Omanta", 6, "Omanta is a personalized research lab operationalizing patient-specific research programs across oncology and rare disease.", "omanta"),
    ("Rasyn", 3, "Rasyn builds foundational AI models for chemistry to design new chemical formulations in weeks instead of years.", "rasyn"),
    ("IMPACT Drones", 2, "IMPACT builds autonomous interceptor drones shipped in sealed containers to protect sites like data centers and power grids.", "impact-drones"),
]

SOURCE_NAME = "Y Combinator Startup Directory"
SOURCE_URL_BASE = "https://www.ycombinator.com/companies/"

STARTUPS = [
    {
        "entityName": name,
        "employeeCount": emp,
        "description": desc,
        "source_url": f"{SOURCE_URL_BASE}{slug}",
    }
    for name, emp, desc, slug in _RAW
]
