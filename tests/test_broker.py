import asyncio

from mechabellum_replay_parser.events.in_memory import InMemoryBroker
from mechabellum_replay_parser.events.schemas import UIEvent


def _run(coro):
    return asyncio.run(coro)


def test_publish_delivers_to_subscriber():
    async def _test():
        broker = InMemoryBroker()
        queue: asyncio.Queue = asyncio.Queue()
        broker.subscribe(queue)

        event = UIEvent(type="test", payload={"hello": "world"})
        await broker.publish(event)

        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.type == "test"
        assert received.payload == {"hello": "world"}
        broker.unsubscribe(queue)

    _run(_test())


def test_publish_fans_out_to_multiple_subscribers():
    async def _test():
        broker = InMemoryBroker()
        q1: asyncio.Queue = asyncio.Queue()
        q2: asyncio.Queue = asyncio.Queue()
        broker.subscribe(q1)
        broker.subscribe(q2)

        event = UIEvent(type="broadcast", payload={})
        await broker.publish(event)

        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert r1.type == "broadcast"
        assert r2.type == "broadcast"
        broker.unsubscribe(q1)
        broker.unsubscribe(q2)

    _run(_test())


def test_unsubscribe_stops_delivery():
    async def _test():
        broker = InMemoryBroker()
        queue: asyncio.Queue = asyncio.Queue()
        broker.subscribe(queue)
        broker.unsubscribe(queue)

        event = UIEvent(type="ghost", payload={})
        await broker.publish(event)

        assert queue.empty()

    _run(_test())


def test_publish_no_subscribers_does_not_raise():
    async def _test():
        broker = InMemoryBroker()
        event = UIEvent(type="dropped", payload={})
        await broker.publish(event)  # should not raise

    _run(_test())


def test_event_id_auto_generated():
    event = UIEvent(type="test", payload={})
    assert event.event_id.startswith("evt_")
    assert len(event.event_id) > 4


def test_two_events_have_distinct_ids():
    e1 = UIEvent(type="test", payload={})
    e2 = UIEvent(type="test", payload={})
    assert e1.event_id != e2.event_id
