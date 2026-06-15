"""Tests for native_ui event dispatching logic.

CoachWindow cannot be tested headlessly (it creates a real Tk root).
These tests cover the _handle_event logic with a mock window so no
display server or Tkinter import is needed.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mechabellum_replay_parser.events.schemas import UIEvent


# ── Mock window ────────────────────────────────────────────────────────────────

class _MockWindow:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._submitted: list[tuple] = []

    def show_idle(self) -> None:
        self.calls.append(("idle",))

    def show_supply_prompt(self, round_num, player_name, on_submit) -> None:
        self.calls.append(("supply", round_num, player_name))
        # Simulate user entering 300 immediately
        self._last_on_submit = on_submit

    def show_loading(self, round_num, player_name) -> None:
        self.calls.append(("loading", round_num, player_name))

    def show_result(self, *, round_num, player_name, summary,
                    coach_text, current_units, placement, constructions,
                    recommendation_id="", on_feedback=None) -> None:
        self.calls.append(("result", round_num, player_name, summary))
        self._last_on_feedback = on_feedback
        self._last_rec_id = recommendation_id

    def show_error(self, message) -> None:
        self.calls.append(("error", message))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _supply_event(rec_id: str = "rec_1", round_num: int = 5, player: str = "P") -> UIEvent:
    return UIEvent(
        type="supply_request",
        payload={"recommendation_id": rec_id, "round": round_num, "player_name": player},
    )


def _ready_event(rec_id: str = "rec_1") -> UIEvent:
    return UIEvent(
        type="recommendation_ready",
        payload={
            "recommendation_id": rec_id,
            "round": 5,
            "player_name": "P",
            "summary": "Buy Arclight",
            "coach_text": "Arclight counters chaff effectively.",
            "current_units": [],
            "constructions": [],
            "placement": [{"unit": "arclight", "x": 0, "y": -90, "action": "new"}],
        },
    )


def _error_event(msg: str = "Parse failed") -> UIEvent:
    return UIEvent(type="error", payload={"message": msg})


def _unknown_event() -> UIEvent:
    return UIEvent(type="some_future_event", payload={})


# ── Import _handle_event without triggering Tkinter ───────────────────────────

def _import_handle_event():
    # Import lazily to avoid importing CoachWindow (which creates tk.Tk) at module load
    from mechabellum_replay_parser.native_ui.main import _handle_event
    return _handle_event


# ── Tests: supply_request ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_supply_request_calls_show_supply_prompt():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_supply_response = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_supply_event(round_num=7, player="Alice"), client, window, loop)

    assert window.calls[0] == ("supply", 7, "Alice")


@pytest.mark.anyio
async def test_supply_on_submit_shows_loading_then_posts():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_supply_response = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_supply_event(rec_id="rec_x", round_num=3, player="Bob"), client, window, loop)

    # Simulate user clicking submit with supply=250
    window._last_on_submit(250, False)

    # Must immediately show loading
    assert ("loading", 3, "Bob") in window.calls

    # Give the event loop a tick to process the scheduled coroutine
    await asyncio.sleep(0)
    client.post_supply_response.assert_called_once_with(
        recommendation_id="rec_x", supply=250, cancelled=False
    )


@pytest.mark.anyio
async def test_supply_cancel_sends_cancelled_true():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_supply_response = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_supply_event(rec_id="rec_c"), client, window, loop)
    window._last_on_submit(None, True)

    await asyncio.sleep(0)
    client.post_supply_response.assert_called_once_with(
        recommendation_id="rec_c", supply=None, cancelled=True
    )


# ── Tests: recommendation_ready ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_recommendation_ready_calls_show_result():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    loop = asyncio.get_running_loop()

    await handle(_ready_event(), client, window, loop)

    assert any(c[0] == "result" for c in window.calls)
    result_call = next(c for c in window.calls if c[0] == "result")
    assert result_call[1] == 5          # round_num
    assert result_call[2] == "P"        # player_name
    assert result_call[3] == "Buy Arclight"  # summary


# ── Tests: error ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_error_event_calls_show_error():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    loop = asyncio.get_running_loop()

    await handle(_error_event("Replay corrupted"), client, window, loop)

    assert ("error", "Replay corrupted") in window.calls


@pytest.mark.anyio
async def test_unknown_event_does_not_crash():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    loop = asyncio.get_running_loop()

    # Should not raise
    await handle(_unknown_event(), client, window, loop)
    assert window.calls == []


# ── Tests: feedback ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_recommendation_ready_provides_on_feedback():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_feedback = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_ready_event(rec_id="rec_fb"), client, window, loop)

    assert hasattr(window, "_last_on_feedback")
    assert window._last_on_feedback is not None
    assert window._last_rec_id == "rec_fb"


@pytest.mark.anyio
async def test_feedback_on_submit_calls_post_feedback():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_feedback = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_ready_event(rec_id="rec_fb2"), client, window, loop)

    # Simulate user clicking 👍
    window._last_on_feedback("rec_fb2", 5, "good", None, None)

    await asyncio.sleep(0)
    client.post_feedback.assert_called_once_with(
        "rec_fb2", 5, "good", None, None
    )


@pytest.mark.anyio
async def test_feedback_thumbs_down_sends_rating_1():
    handle = _import_handle_event()
    window = _MockWindow()
    client = MagicMock()
    client.post_feedback = AsyncMock()
    loop = asyncio.get_running_loop()

    await handle(_ready_event(rec_id="rec_fb3"), client, window, loop)
    window._last_on_feedback("rec_fb3", 1, "bad_strategy", None, None)

    await asyncio.sleep(0)
    call_kwargs = client.post_feedback.call_args
    assert call_kwargs.args[1] == 1  # rating


# ── Tests: UIEvent schema ─────────────────────────────────────────────────────

def test_supply_event_schema():
    event = _supply_event(rec_id="rec_99", round_num=10, player="Test")
    assert event.type == "supply_request"
    assert event.payload["recommendation_id"] == "rec_99"
    assert event.payload["round"] == 10


def test_ready_event_schema():
    event = _ready_event(rec_id="rec_42")
    assert event.type == "recommendation_ready"
    assert event.payload["summary"] == "Buy Arclight"
    assert len(event.payload["placement"]) == 1


def test_error_event_schema():
    event = _error_event("Something went wrong")
    assert event.type == "error"
    assert event.payload["message"] == "Something went wrong"
