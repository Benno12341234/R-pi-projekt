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


def provider_available(provider: str) -> bool:
    if provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    return False
