"""Concrete LLM providers: OpenAI, Ollama, and the offline mock."""
from __future__ import annotations

import re

import httpx

from app.assets.registry import AssetRegistry
from app.config import Settings
from app.llm.base import LLMError, LLMProvider
from app.llm.mock import MockSceneBuilder


class MockProvider(LLMProvider):
    """Rule-based provider — always available, no network or keys required."""

    name = "mock"

    def __init__(self, registry: AssetRegistry) -> None:
        self._registry = registry
        self._builder = MockSceneBuilder(registry)

    async def complete(self, system: str, user: str) -> str:  # noqa: ARG002
        # A multi-sentence script becomes a speech-paced storyboard; a short prompt
        # uses the templated scene builder (nicer fan-out visuals).
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", (user or "").strip()) if s.strip()]
        if len(sentences) >= 3:
            from app.scene.director import deterministic_storyboard

            return deterministic_storyboard(user, self._registry).model_dump_json(by_alias=True)
        return self._builder.build(user).model_dump_json(by_alias=True)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, object] = {
            "api_key": settings.openai_api_key,
            "timeout": settings.llm_timeout,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._client = AsyncOpenAI(**kwargs)  # type: ignore[arg-type]
        self._model = settings.openai_model
        self._temperature = settings.llm_temperature
        self._has_key = bool(settings.openai_api_key)

    async def available(self) -> bool:
        return self._has_key

    async def complete(self, system: str, user: str) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # network, auth, quota, etc.
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        return resp.choices[0].message.content or ""


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self._host = settings.ollama_host.rstrip("/")
        self._model = settings.ollama_model
        self._temperature = settings.llm_temperature
        self._timeout = settings.llm_timeout
        self._max_tokens = settings.llm_max_tokens
        self._keep_alive = settings.ollama_keep_alive
        self._num_ctx = settings.ollama_num_ctx

    async def available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self._host}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            # NOTE: Ollama's grammar-constrained `format: "json"` is very slow here;
            # we rely on the prompt + robust JSON extraction downstream instead.
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
                "num_ctx": self._num_ctx,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._host}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        return data.get("message", {}).get("content", "")
