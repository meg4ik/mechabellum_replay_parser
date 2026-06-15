"""Entry point for the host-native Tkinter process.

Run with:
    uv run python -m mechabellum_replay_parser.native_ui.main
or:
    mech-native-ui
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from mechabellum_replay_parser.events.schemas import UIEvent

from .client import CoreAPIClient

load_dotenv()


async def _handle_event(event: UIEvent, client: CoreAPIClient) -> None:
    """Dispatch incoming events to the appropriate Tkinter handler.

    Phase 3 will add supply_request and recommendation_ready handling here.
    """
    print(f"[native_ui] Event received: type={event.type!r}  id={event.event_id}")


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
