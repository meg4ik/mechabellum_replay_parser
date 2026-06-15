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
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(event.model_dump_json())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        broker.unsubscribe(queue)
