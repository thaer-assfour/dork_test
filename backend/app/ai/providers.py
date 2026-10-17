"""AI provider abstraction. Two providers, both optional and user-configured:

- openai_compatible: any OpenAI-style /chat/completions endpoint. Covers a local
  model via Ollama (http://localhost:11434/v1, free + self-hosted), plus hosted
  gateways (OpenRouter, Groq, Together, Gemini's OpenAI-compatible endpoint, ...).
- anthropic: the official Anthropic API (needs API billing, which is separate
  from a Claude Pro/Max subscription).

The provider only does text completion; feature prompts live in service.py.
"""
from __future__ import annotations

import httpx


class AIError(RuntimeError):
    pass


class AIProvider:
    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            resp = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=120.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIError(f"AI request failed: {exc}") from exc
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError(f"unexpected AI response shape: {exc}") from exc


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        if not self.api_key:
            raise AIError("anthropic: missing API key")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise AIError("anthropic SDK not installed") from exc
        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise AIError(f"anthropic request failed: {exc}") from exc
        if getattr(resp, "stop_reason", None) == "refusal":
            raise AIError("anthropic declined the request")
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def build_provider(provider: str, base_url: str, api_key: str, model: str) -> AIProvider:
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
