"""Entry point for the host-native Tkinter process.

Run with:
    uv run python -m mechabellum_replay_parser.native_ui.main
or:
    mech-native-ui

This process connects to the Docker core via WebSocket, listens for events,
shows Tkinter dialogs / board windows, and posts responses back via HTTP.
No game logic lives here.
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from mechabellum_replay_parser.events.schemas import (
    RecommendationReadyPayload,
    SupplyRequestPayload,
    UIEvent,
)

from .client import CoreAPIClient
from .display import ask_supply, show_board_async

load_dotenv()


async def _handle_event(event: UIEvent, client: CoreAPIClient) -> None:
    if event.type == "supply_request":
        payload = SupplyRequestPayload.model_validate(event.payload)
        # ask_supply uses Tkinter — run in a thread so we don't block the event loop.
        # Tkinter-in-thread works here for the same reason show_board_async already does it.
        supply = await asyncio.to_thread(ask_supply, payload.round)
        await client.post_supply_response(
            recommendation_id=payload.recommendation_id,
            supply=supply,
            cancelled=(supply is None),
        )

    elif event.type == "recommendation_ready":
        payload = RecommendationReadyPayload.model_validate(event.payload)
        show_board_async(
            payload.current_units,
            payload.placement,
            payload.round,
            payload.player_name,
            payload.constructions,
        )

    elif event.type == "error":
        print(f"[native_ui] Server error: {event.payload.get('message')}")

    else:
        print(f"[native_ui] Unknown event type: {event.type!r}")


async def _run() -> None:
    base_url = os.getenv("CORE_API_URL", "http://localhost:8000")
    ws_url = os.getenv("CORE_WS_URL", "ws://localhost:8000/events/ws")

    client = CoreAPIClient(base_url=base_url, ws_url=ws_url)
    print(f"[native_ui] Connecting to {ws_url} …")

    async for event in client.events():
        await _handle_event(event, client)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
