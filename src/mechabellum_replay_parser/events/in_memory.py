from __future__ import annotations

import asyncio

from .schemas import UIEvent


class InMemoryBroker:
    """Fan-out event broker backed by asyncio queues.

    Each subscriber registers a Queue; publish() puts the event into every queue.
    The WebSocket route owns the queue lifetime (subscribe/unsubscribe).

    Pending supply: the last supply_request that has not yet been answered is
    stored so late-connecting WebSocket clients receive it immediately on connect.
    """

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[UIEvent]] = set()
        self._pending_supply: UIEvent | None = None

    async def publish(self, event: UIEvent) -> None:
        if event.type == "supply_request":
            self._pending_supply = event
        elif event.type in ("recommendation_ready", "error"):
            self._pending_supply = None
        for q in self._queues:
            await q.put(event)

    def pending_supply(self) -> UIEvent | None:
        return self._pending_supply

    def clear_pending_supply(self) -> None:
        self._pending_supply = None

    def subscriber_count(self) -> int:
        return len(self._queues)

    def subscribe(self, queue: asyncio.Queue[UIEvent]) -> None:
        self._queues.add(queue)

    def unsubscribe(self, queue: asyncio.Queue[UIEvent]) -> None:
        self._queues.discard(queue)
