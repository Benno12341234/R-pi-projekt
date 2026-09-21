import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TierModels:
    anthropic: Optional[str] = None
    openai: Optional[str] = None


DEFAULT_PROVIDER_PRIORITY = ["anthropic", "openai"]

# Cheapest capable model per tier, per provider. Edit these when a provider
# ships a new model - nothing else in the router needs to change.
DEFAULT_TIERS = {
    "simple": TierModels(anthropic="claude-haiku-4-5", openai="gpt-4o-mini"),
    "standard": TierModels(anthropic="claude-sonnet-5", openai="gpt-4o"),
    "complex": TierModels(anthropic="claude-opus-5", openai="gpt-4.1"),
}


# Cost guard: refuse to make more than this many paid API calls per window.
# Override via env vars if 60/hour is too tight or too loose for your use case.
DEFAULT_RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("MODEL_ROUTER_RATE_LIMIT_MAX_REQUESTS", "60"))
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("MODEL_ROUTER_RATE_LIMIT_WINDOW_SECONDS", "3600"))


def provider_available(provider: str) -> bool:
    if provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    return False
