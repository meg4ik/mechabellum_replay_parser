from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal async interface all LLM backends must satisfy."""

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
        temperature: float = 0.2,
    ) -> dict:
        """Return a parsed JSON dict from the model."""
        ...

    def stream_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Return an async iterator yielding text chunks."""
        ...
