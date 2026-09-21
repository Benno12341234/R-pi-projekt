"""Demo for the model router. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY
before running - the router uses whichever provider(s) it finds a key for."""

from model_router import ModelRouter

router = ModelRouter()

prompts = [
    "Hi!",
    "Summarize this project's README in two sentences.",
    "Analyze the trade-offs of a distributed cache vs. an in-process cache "
    "for a Raspberry Pi cluster, and recommend an architecture.",
]

for prompt in prompts:
    result = router.route(prompt)
    print(f"[{result.tier} -> {result.provider}/{result.model}] {prompt[:60]!r}")
    print(result.text)
    print("-" * 40)
