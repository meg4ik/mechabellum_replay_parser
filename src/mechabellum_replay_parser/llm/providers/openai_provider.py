"""Async OpenAI backend."""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

# o-series reasoning models don't accept a custom temperature parameter.
_O_SERIES_RE = re.compile(r"^o\d")


def _supports_temperature(model: str) -> bool:
    return not _O_SERIES_RE.match(model)


class OpenAIProvider:
    """Wraps AsyncOpenAI with the LLMProvider interface.

    The ``AsyncOpenAI`` client is created lazily on the first call so that
    importing this module does not raise when ``OPENAI_API_KEY`` is absent
    (e.g. during test collection).
    """

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str | None = None,
    ) -> None:
        self._client: AsyncOpenAI | None = client
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: dict | None = None,  # reserved for structured-output support
        temperature: float = 0.2,
    ) -> dict:
        _ = schema  # not yet used; future: pass as json_schema to the API
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        if _supports_temperature(self._model):
            kwargs["temperature"] = temperature
        response = await self._get_client().chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    async def _stream_gen(
        self, system: str, user: str, temperature: float
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
        }
        if _supports_temperature(self._model):
            kwargs["temperature"] = temperature
        stream = await self._get_client().chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def stream_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        return self._stream_gen(system, user, temperature)
