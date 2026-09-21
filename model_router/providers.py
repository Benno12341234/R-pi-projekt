import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ProviderError(Exception):
    """Raised when a provider fails to complete a request (auth, rate limit,
    connection, or API error) so the router can fall back to the next one."""


@dataclass
class CompletionResult:
    text: str
    provider: str
    model: str


@dataclass
class ImageInput:
    data_b64: str
    media_type: str  # e.g. "image/jpeg"

    @classmethod
    def from_file(cls, path: Path, media_type: str = "image/jpeg") -> "ImageInput":
        data_b64 = base64.standard_b64encode(Path(path).read_bytes()).decode("utf-8")
        return cls(data_b64=data_b64, media_type=media_type)


class Provider:
    name: str

    def complete(
        self, model: str, prompt: str, system: Optional[str], max_tokens: int, image: Optional[ImageInput] = None,
    ) -> CompletionResult:
        raise NotImplementedError


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self):
        import anthropic
        self._anthropic = anthropic
        self._client = anthropic.Anthropic()

    def complete(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 16000,
        image: Optional[ImageInput] = None,
    ) -> CompletionResult:
        anthropic = self._anthropic

        if image:
            content = [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": image.media_type, "data": image.data_b64},
                },
                {"type": "text", "text": prompt},
            ]
        else:
            content = prompt

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
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

    def complete(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 16000,
        image: Optional[ImageInput] = None,
    ) -> CompletionResult:
        openai = self._openai

        if image:
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{image.media_type};base64,{image.data_b64}"}},
            ]
        else:
            user_content = prompt

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content})

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
