"""Common types for LLM providers."""
from __future__ import annotations

import abc


class LLMError(RuntimeError):
    """Raised when a provider fails to produce a usable completion."""


class LLMProvider(abc.ABC):
    """A text-in / text-out chat completion provider.

    Providers return the raw model text (expected to be JSON). Parsing and
    validation happen downstream in the scene generator, so every provider —
    including the offline mock — goes through the exact same code path.
    """

    name: str = "base"

    @abc.abstractmethod
    async def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        """Return the model's raw text response."""

    async def available(self) -> bool:  # noqa: D401 - simple predicate
        """Whether this provider is currently usable."""
        return True
