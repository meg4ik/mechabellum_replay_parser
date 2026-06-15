"""Deterministic stub provider — no network, for unit tests."""
from __future__ import annotations

from collections.abc import AsyncIterator


class LocalProvider:
    """Returns canned responses without any network call.

    Pass *json_response* for :meth:`complete_json` calls and
    *text_chunks* for :meth:`stream_text` calls.
    """

    def __init__(
        self,
        json_response: dict | None = None,
        text_chunks: list[str] | None = None,
    ) -> None:
        self._json: dict = json_response or {}
        self._chunks: list[str] = text_chunks or []

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
        temperature: float = 0.2,
    ) -> dict:
        return dict(self._json)

    async def _text_gen(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    def stream_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        return self._text_gen()
