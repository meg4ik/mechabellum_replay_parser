from __future__ import annotations

import asyncio

from .schemas import UIEvent


class InMemoryBroker:
    """Fan-out event broker backed by asyncio queues.

    Each subscriber registers a Queue; publish() puts the event into every queue.
    The WebSocket route owns the queue lifetime (subscribe/unsubscribe).
    """

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[UIEvent]] = set()

    async def publish(self, event: UIEvent) -> None:
        for q in self._queues:
            await q.put(event)

    def subscribe(self, queue: asyncio.Queue[UIEvent]) -> None:
        self._queues.add(queue)

    def unsubscribe(self, queue: asyncio.Queue[UIEvent]) -> None:
        self._queues.discard(queue)
