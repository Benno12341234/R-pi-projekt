from dataclasses import dataclass
from typing import Dict, Optional

from .complexity import classify_complexity
from .config import DEFAULT_PROVIDER_PRIORITY, DEFAULT_TIERS, provider_available
from .providers import AnthropicProvider, OpenAIProvider, Provider, ProviderError

_PROVIDER_CLASSES = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


@dataclass
class RoutingResult:
    text: str
    provider: str
    model: str
    tier: str


class ModelRouter:
    """Routes a prompt to the cheapest model tier that can plausibly handle
    it, falling back across providers when one is unavailable or errors."""

    def __init__(self, tiers=None, provider_priority=None):
        self._tiers = tiers or DEFAULT_TIERS
        self._provider_priority = provider_priority or DEFAULT_PROVIDER_PRIORITY
        self._provider_instances: Dict[str, Provider] = {}

    def _get_provider(self, name: str) -> Provider:
        if name not in self._provider_instances:
            self._provider_instances[name] = _PROVIDER_CLASSES[name]()
        return self._provider_instances[name]

    def route(
        self,
        prompt: str,
        tier: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 16000,
    ) -> RoutingResult:
        chosen_tier = tier or classify_complexity(prompt)
        if chosen_tier not in self._tiers:
            raise ValueError(f"unknown tier '{chosen_tier}', expected one of {list(self._tiers)}")

        tier_models = self._tiers[chosen_tier]
        errors = []

        for provider_name in self._provider_priority:
            model = getattr(tier_models, provider_name, None)
            if not model or not provider_available(provider_name):
                continue
            try:
                provider = self._get_provider(provider_name)
                result = provider.complete(model, prompt, system=system, max_tokens=max_tokens)
                return RoutingResult(text=result.text, provider=result.provider, model=result.model, tier=chosen_tier)
            except ProviderError as exc:
                errors.append(str(exc))
                continue

        raise RuntimeError(
            f"no provider could handle tier '{chosen_tier}': "
            + ("; ".join(errors) if errors else "no provider configured/available (check API keys)")
        )
