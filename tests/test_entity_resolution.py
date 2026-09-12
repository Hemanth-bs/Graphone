import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.entity_resolution import EntityResolver

test_inputs = [
    "OpenAI",
    "OpenAI, Inc.",
    "Open AI",
    "openai.com",
    "Anthropic PBC",
    "Anthropic AI",
    "Mistral",
    "MistralAI",
    "Hugging Face Inc",
    "HF",
    "DeepSeek-AI",
    "Deep Seek",
    "A totally novel startup nobody has heard of LLC",  # should register as new
    "A Totally Novel Startup Nobody Has Heard Of",       # should fuzzy-match the above
]

resolver = EntityResolver()
records = resolver.resolve_batch(test_inputs)

print(f"{'RAW':45} {'CANONICAL':25} {'METHOD':12} CONF")
for r in records:
    print(f"{r.raw_name:45} {r.canonical_name:25} {r.method:12} {r.confidence:.2f}")

# sanity checks
assert resolver.resolve("OpenAI, Inc.").canonical_name == "OpenAI"
assert resolver.resolve("Deep Seek").canonical_name == "DeepSeek"
assert resolver.resolve("HF").canonical_name == "Hugging Face"
new1 = resolver.resolve("Some Brand New Startup Xyzabc LLC")
new2 = resolver.resolve("Some Brand New Startup Xyzabc")
assert new1.canonical_name == new2.canonical_name, "fuzzy match should catch near-duplicate new entity"

# Regression test: "AI" must NOT be treated as a strippable legal suffix
# (like "Inc."/"Ltd."), because it's frequently part of the actual brand
# name. Stripping it previously caused unrelated companies whose names
# differ only by a trailing "AI" to collapse into the same canonical
# entity purely by coincidence of normalization.
together_ai = resolver.resolve("Together AI")
together_unrelated = resolver.resolve("Together Data Systems")  # distinct, unrelated company
assert together_ai.canonical_name != together_unrelated.canonical_name, (
    "'Together AI' and an unrelated 'Together Data Systems' must not be "
    "merged just because 'AI'/'Systems' normalize away"
)
# But a *genuine* near-duplicate of the same brand should still fuzzy-match.
together_ai_again = resolver.resolve("Together AI, Inc.")
assert together_ai_again.canonical_name == together_ai.canonical_name, (
    "genuine variants of the same brand (legal-suffix differences) should still match"
)

print("\nAll assertions passed.")
