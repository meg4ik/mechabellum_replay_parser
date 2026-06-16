"""Entry point for the host-native Tkinter process.

Architecture:
  • CoachWindow runs on the main thread (Tkinter requirement).
  • asyncio event loop runs in a daemon background thread.
  • Background thread → Tkinter:  window.show_*() → root.after(0, ...).
  • Tkinter → background thread:  asyncio.run_coroutine_threadsafe(coro, loop).

Run with:
    uv run python -m mechabellum_replay_parser.native_ui.main
or:
    mech-native-ui
"""

from __future__ import annotations

import asyncio
import os
import threading

from dotenv import load_dotenv

from mechabellum_replay_parser.events.schemas import (
    RecommendationReadyPayload,
    SupplyRequestPayload,
    UIEvent,
)

from .client import CoreAPIClient
from .display import CoachWindow

load_dotenv()


async def _handle_event(
    event: UIEvent,
    client: CoreAPIClient,
    window: CoachWindow,
    loop: asyncio.AbstractEventLoop,
) -> None:
    if event.type == "supply_request":
        payload = SupplyRequestPayload.model_validate(event.payload)

        def on_submit(supply: int | None, cancelled: bool) -> None:
            # Called on the Tkinter main thread (button click).
            window.show_loading(payload.round, payload.player_name)
            asyncio.run_coroutine_threadsafe(
                client.post_supply_response(
                    recommendation_id=payload.recommendation_id,
                    supply=supply,
                    cancelled=cancelled,
                ),
                loop,
            )

        window.show_supply_prompt(payload.round, payload.player_name, on_submit)

    elif event.type == "recommendation_ready":
        payload = RecommendationReadyPayload.model_validate(event.payload)

        def on_feedback(
            rec_id: str,
            rating: int,
            label: str | None,
            comment: str | None,
            followed_plan: bool | None,
        ) -> None:
            asyncio.run_coroutine_threadsafe(
                client.post_feedback(rec_id, rating, label, comment, followed_plan),
                loop,
            )

        window.show_result(
            round_num=payload.round,
            player_name=payload.player_name,
            summary=payload.summary,
            coach_text=payload.coach_text,
            current_units=payload.current_units,
            placement=payload.placement,
            constructions=payload.constructions,
            recommendation_id=payload.recommendation_id,
            on_feedback=on_feedback,
        )

    elif event.type == "error":
        message = event.payload.get("message", "Неизвестная ошибка")
        window.show_error(message)

    else:
        print(f"[native_ui] Unknown event type: {event.type!r}")


async def _run_async(window: CoachWindow, loop: asyncio.AbstractEventLoop) -> None:
    base_url = os.getenv("CORE_API_URL", "http://localhost:8000")
    ws_url = os.getenv("CORE_WS_URL", "ws://localhost:8000/events/ws")

    client = CoreAPIClient(base_url=base_url, ws_url=ws_url)
    print(f"[native_ui] Connecting to {ws_url} …")

    async for event in client.events(
        on_connect=window.show_connected,
        on_disconnect=window.show_backend_unavailable,
    ):
        await _handle_event(event, client, window, loop)


def _start_async_thread(window: CoachWindow) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_async(window, loop))
    except Exception as exc:
        print(f"[native_ui] Async thread error: {exc}")
    finally:
        loop.close()


def main() -> None:
    window = CoachWindow()

    bg = threading.Thread(target=_start_async_thread, args=(window,), daemon=True)
    bg.start()

    window.mainloop()


if __name__ == "__main__":
    main()
