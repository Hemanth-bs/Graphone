import json

# Real papers sourced from https://github.com/AtharvaDomale/Daily-HuggingFace-AI-Papers
# (which itself aggregates https://huggingface.co/papers/trending), cross-referenced
# with LIVE star counts pulled directly from api.github.com on 2026-09-12.
RESEARCH_PAPERS = [
    {"title": "EnvHarness: Awakening Static Worlds for Agent Learning", "paper_url": "https://arxiv.org/abs/2608.19880", "github_url": "https://github.com/google-research/envharness", "github_stars": 537},
    {"title": "FACET: Preserving Source Intent and Executable State in Terminal Task Synthesis", "paper_url": "https://arxiv.org/abs/2608.18580", "github_url": "https://github.com/StoKou/FACET-Terminal", "github_stars": 121},
    {"title": "4DAnyone: Create Anyone in 4D from a Casual Monocular Video", "paper_url": "https://arxiv.org/abs/2608.20335", "github_url": "https://github.com/ant-research/4DAnyone", "github_stars": 1276},
    {"title": "SWE-bench Science: Can Coding Agents Resolve Engineering Tasks in Science?", "paper_url": "https://arxiv.org/abs/2608.19799", "github_url": "https://github.com/OpenMOSS/SWE-bench-Science", "github_stars": 80},
    {"title": "WithEveryone: Unified Planning and Identity Grounding for Group Image Generation", "paper_url": "https://arxiv.org/abs/2608.20336", "github_url": "https://github.com/doby-xu/WithEveryone", "github_stars": 45},
    {"title": "MemTrapBench: Benchmarking Cognitive Traps in LLM Memory Use", "paper_url": "https://arxiv.org/abs/2608.20202", "github_url": "https://github.com/zjunlp/MemTrapBench", "github_stars": 5},
    {"title": "ForgeWM: Progressive Causal Training for Few-Step Action-Conditioned Video World Models", "paper_url": "https://arxiv.org/abs/2608.14022", "github_url": "https://github.com/asdfo123/ForgeWM", "github_stars": 107},
    {"title": "FlashPrefill V2: Block-Sparse Prefill Attention for Long-Context LLM Serving", "paper_url": "https://arxiv.org/abs/2608.19758", "github_url": "https://github.com/qhfan/FlashPrefillv2", "github_stars": 27},
    {"title": "Hierarchical Self-Improvement: A Framework for Task-Specific Evolvable Agent Harnesses", "paper_url": "https://arxiv.org/abs/2608.08466", "github_url": "https://github.com/TailinZhou/hsi", "github_stars": 11},
    {"title": "tau_0-VLA: a Hierarchical Robot Foundation Model with World-Model-Guided Test-Time Computation", "paper_url": "https://arxiv.org/abs/2608.16885", "github_url": "https://github.com/sii-research/tau-0-vla", "github_stars": 614},
    {"title": "Towards Quantifying Benchmark Optimization in ASR Models", "paper_url": "https://arxiv.org/abs/2608.19936", "github_url": "https://github.com/HumeAI/asr-benchmark-optimization", "github_stars": 12},
    {"title": "TinyCast: Probabilistic Zero-Shot Forecasting with Computed Periodicity", "paper_url": "https://arxiv.org/abs/2608.15767", "github_url": "https://github.com/raws-labs/tinycast", "github_stars": 7},
    {"title": "NARU: A Benchmark for NARrative Evolution and Cultural Nuance Understanding in Japanese Extreme Long Video", "paper_url": "https://arxiv.org/abs/2608.13210", "github_url": "https://github.com/infinimind-inc/naru_benchmark", "github_stars": 3},
    {"title": "PolicyGuide: From Guarding One Action to Guiding the Whole Workflow for Policy-Compliant LLM Agents", "paper_url": "https://arxiv.org/abs/2608.19861", "github_url": "https://github.com/erjui/PolicyGuide", "github_stars": 0},
    {"title": "Listening Forward: Next Patch Embedding Prediction Enables Scalable Audio Learners", "paper_url": "https://arxiv.org/abs/2608.19863", "github_url": "https://github.com/umbertocappellazzo/nape", "github_stars": 18},
    {"title": "FlowEvo: Self-Evolving Agents through the Co-Evolution of Workflows and Executable Skills", "paper_url": "https://arxiv.org/abs/2607.21596", "github_url": "https://github.com/DEFENSE-SEU/FlowEvo", "github_stars": 20},
    {"title": "QuoteBench: How Matched Scores Can Hide Command-Path Failures", "paper_url": "https://arxiv.org/abs/2608.13547", "github_url": "https://github.com/LeonardNJU/quoteBench", "github_stars": 3},
    {"title": "GOAG: Generative and Object-Agnostic Grasp Planner for Dexterous Robotic Manipulation", "paper_url": "https://arxiv.org/abs/2608.19759", "github_url": "https://github.com/CEA-LIST/GOAG", "github_stars": 9},
    {"title": "CoToGrasp: Contact-Topology-Conditioned Dexterous Grasp Synthesis via Canonical Workspace Learning", "paper_url": "https://arxiv.org/abs/2608.19776", "github_url": "https://github.com/CEA-LIST/CoToGrasp", "github_stars": 7},
]

# arXiv IDs of form YYMM.NNNNN encode the submission year/month (2608 -> Aug 2026,
# 2607 -> Jul 2026); we derive published_date from this rather than guessing.
for p in RESEARCH_PAPERS:
    arxiv_id = p["paper_url"].rsplit("/", 1)[-1]
    yy, mm = arxiv_id[0:2], arxiv_id[2:4]
    p["published_date"] = f"20{yy}-{mm}-01T00:00:00"  # day unknown -> normalized to 1st of month
    p["authors"] = []  # not scraped in this pass; HF page lists authors per-paper, omitted to avoid guessing
    p["source_name"] = "Hugging Face Daily Papers"
    p["source_url"] = "https://huggingface.co/papers/trending"

if __name__ == "__main__":
    print(json.dumps(RESEARCH_PAPERS, indent=2)[:500])
