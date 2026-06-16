from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mechabellum_replay_parser.events.in_memory import InMemoryBroker
from mechabellum_replay_parser.events.schemas import UIEvent

router = APIRouter()


def _broker(websocket: WebSocket) -> InMemoryBroker:
    return websocket.app.state.broker


@router.websocket("/events/ws")
async def events_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    broker = _broker(websocket)
    queue: asyncio.Queue[UIEvent] = asyncio.Queue()
    broker.subscribe(queue)
    print(f"[ws] Client connected. Subscribers now: {broker.subscriber_count()}")
    try:
        # Replay pending supply_request for clients that connected after it was published
        pending = broker.pending_supply()
        if pending is not None:
            print(f"[ws] Replaying pending supply_request to new client: {pending.event_id}")
            await websocket.send_text(pending.model_dump_json())
        while True:
            event = await queue.get()
            print(f"[ws] Sending event to client: type={event.type} id={event.event_id}")
            await websocket.send_text(event.model_dump_json())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        broker.unsubscribe(queue)
        print(f"[ws] Client disconnected. Subscribers now: {broker.subscriber_count()}")
