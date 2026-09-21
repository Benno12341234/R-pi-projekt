from dataclasses import dataclass
from typing import Optional


class ProviderError(Exception):
    """Raised when a provider fails to complete a request (auth, rate limit,
    connection, or API error) so the router can fall back to the next one."""


@dataclass
class CompletionResult:
    text: str
    provider: str
    model: str


class Provider:
    name: str

    def complete(self, model: str, prompt: str, system: Optional[str], max_tokens: int) -> CompletionResult:
        raise NotImplementedError


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self):
        import anthropic
        self._anthropic = anthropic
        self._client = anthropic.Anthropic()

    def complete(self, model: str, prompt: str, system: Optional[str] = None, max_tokens: int = 16000) -> CompletionResult:
        anthropic = self._anthropic
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise ProviderError(f"anthropic rate limited: {exc}") from exc
        except anthropic.AuthenticationError as exc:
            raise ProviderError(f"anthropic auth failed: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"anthropic connection error: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"anthropic API error ({exc.status_code}): {exc.message}") from exc

        text = next((block.text for block in response.content if block.type == "text"), "")
        return CompletionResult(text=text, provider=self.name, model=model)


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self):
        import openai
        self._openai = openai
        self._client = openai.OpenAI()

    def complete(self, model: str, prompt: str, system: Optional[str] = None, max_tokens: int = 16000) -> CompletionResult:
        openai = self._openai
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
        except openai.RateLimitError as exc:
            raise ProviderError(f"openai rate limited: {exc}") from exc
        except openai.AuthenticationError as exc:
            raise ProviderError(f"openai auth failed: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise ProviderError(f"openai connection error: {exc}") from exc
        except openai.APIStatusError as exc:
            raise ProviderError(f"openai API error: {exc}") from exc

        text = response.choices[0].message.content or ""
        return CompletionResult(text=text, provider=self.name, model=model)
