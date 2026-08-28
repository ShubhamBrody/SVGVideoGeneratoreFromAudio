"""Provider selection and the completion gateway with automatic mock fallback."""
from __future__ import annotations

from app.assets.registry import AssetRegistry
from app.config import Settings
from app.llm.base import LLMError, LLMProvider
from app.llm.providers import MockProvider, OllamaProvider, OpenAIProvider


class LLMGateway:
    """Wraps the active provider and falls back to the mock on any failure."""

    def __init__(self, provider: LLMProvider, fallback: MockProvider) -> None:
        self._provider = provider
        self._fallback = fallback

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def complete(self, system: str, user: str) -> tuple[str, str]:
        """Return ``(raw_text, provider_label)``."""
        if self._provider is self._fallback:
            return await self._fallback.complete(system, user), self._fallback.name
        try:
            out = await self._provider.complete(system, user)
            if not out or not out.strip():
                raise LLMError("empty response")
            return out, self._provider.name
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            out = await self._fallback.complete(system, user)
            return out, f"mock (fallback: {type(exc).__name__})"


async def build_gateway(settings: Settings, registry: AssetRegistry) -> LLMGateway:
    mock = MockProvider(registry)
    choice = (settings.llm_provider or "auto").lower()

    async def make_openai() -> LLMProvider | None:
        if not settings.openai_api_key:
            return None
        try:
            provider = OpenAIProvider(settings)
        except Exception:
            return None
        return provider if await provider.available() else None

    async def make_ollama() -> LLMProvider | None:
        provider = OllamaProvider(settings)
        return provider if await provider.available() else None

    if choice == "mock":
        provider: LLMProvider = mock
    elif choice == "openai":
        provider = await make_openai() or mock
    elif choice == "ollama":
        provider = await make_ollama() or mock
    else:  # auto: first configured provider, else mock
        provider = await make_openai() or await make_ollama() or mock

    return LLMGateway(provider, mock)
