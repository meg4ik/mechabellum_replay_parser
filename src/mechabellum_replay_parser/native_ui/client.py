from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import httpx2 as httpx
import websockets
import websockets.exceptions

from mechabellum_replay_parser.events.schemas import UIEvent


class CoreAPIClient:
    """Connects the native Tkinter process to the Docker core API."""

    def __init__(self, base_url: str, ws_url: str) -> None:
        self.base_url = base_url
        self.ws_url = ws_url

    async def post_supply_response(
        self,
        recommendation_id: str,
        supply: int | None,
        cancelled: bool = False,
    ) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/ui/supply-response",
                json={
                    "recommendation_id": recommendation_id,
                    "supply": supply,
                    "cancelled": cancelled,
                },
                timeout=10.0,
            )

    async def events(self) -> AsyncGenerator[UIEvent, None]:
        """Yields UIEvents from the WebSocket; reconnects automatically on failure."""
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    print(f"[native_ui] Connected to {self.ws_url}")
                    async for message in ws:
                        data = json.loads(message)
                        yield UIEvent.model_validate(data)
            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException,
                OSError,
            ) as exc:
                print(f"[native_ui] WebSocket error: {exc}. Reconnecting in 2 s...")
                await asyncio.sleep(2)
