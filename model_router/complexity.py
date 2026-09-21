_COMPLEX_KEYWORDS = (
    "analyze", "analyse", "architecture", "algorithm", "debug", "optimize",
    "refactor", "design a", "prove", "derive", "compare", "in detail",
    "step by step", "research", "implement", "trade-off", "tradeoff",
)
_SIMPLE_STARTS = ("hi", "hello", "hey", "thanks", "thank you", "yes", "no", "ok", "okay")


def classify_complexity(prompt: str) -> str:
    """Cheap heuristic: short greetings are 'simple', long or jargon-heavy
    prompts are 'complex', everything else is 'standard'."""
    text = prompt.strip().lower()
    word_count = len(text.split())

    if word_count <= 4 and any(text.startswith(s) for s in _SIMPLE_STARTS):
        return "simple"

    keyword_hits = sum(1 for kw in _COMPLEX_KEYWORDS if kw in text)
    if keyword_hits >= 2 or word_count > 120:
        return "complex"
    if keyword_hits == 1 or word_count > 25:
        return "standard"
    return "simple"
