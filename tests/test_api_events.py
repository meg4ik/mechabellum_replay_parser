"""Tests for event schemas and the /feedback API endpoint."""

import pytest
from fastapi.testclient import TestClient

from mechabellum_replay_parser.api.app import app
from mechabellum_replay_parser.events.schemas import (
    RecommendationReadyPayload,
    SupplyRequestPayload,
    UIEvent,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── Event schema: supply_request ──────────────────────────────────────────────


def test_supply_request_payload_round_trip():
    payload = SupplyRequestPayload(
        recommendation_id="rec_99",
        round=7,
        player_name="Alice",
    )
    event = UIEvent(type="supply_request", payload=payload.model_dump())
    restored = SupplyRequestPayload.model_validate(event.payload)
    assert restored.recommendation_id == "rec_99"
    assert restored.round == 7
    assert restored.player_name == "Alice"


def test_supply_request_serializes_to_dict():
    payload = SupplyRequestPayload(recommendation_id="rec_1", round=3, player_name="P")
    d = payload.model_dump()
    assert d["recommendation_id"] == "rec_1"
    assert d["round"] == 3
    assert d["player_name"] == "P"


# ── Event schema: recommendation_ready ───────────────────────────────────────


def test_recommendation_ready_payload_round_trip():
    payload = RecommendationReadyPayload(
        recommendation_id="rec_42",
        round=5,
        player_name="Bob",
        summary="Buy Arclight",
        coach_text="Arclight counters air.",
        current_units=[{"name": "crawler", "index": 0}],
        constructions=[],
        placement=[{"unit": "arclight", "x": 0, "y": -90, "action": "new"}],
    )
    event = UIEvent(type="recommendation_ready", payload=payload.model_dump())
    restored = RecommendationReadyPayload.model_validate(event.payload)
    assert restored.recommendation_id == "rec_42"
    assert restored.summary == "Buy Arclight"
    assert len(restored.placement) == 1


def test_recommendation_ready_placement_structure():
    payload = RecommendationReadyPayload(
        recommendation_id="rec_1",
        round=1,
        player_name="P",
        summary="Hold",
        coach_text="Keep units.",
        current_units=[],
        constructions=[],
        placement=[
            {"unit": "crawler", "x": -40, "y": -80, "action": "keep"},
            {"unit": "arclight", "x": 0, "y": -90, "action": "new"},
        ],
    )
    assert payload.placement[0]["action"] == "keep"
    assert payload.placement[1]["action"] == "new"


# ── Event schema: UIEvent type field ─────────────────────────────────────────


def test_ui_event_type_preserved():
    for event_type in ("supply_request", "recommendation_ready", "error"):
        e = UIEvent(type=event_type, payload={})
        assert e.type == event_type


def test_ui_event_unknown_type_allowed():
    e = UIEvent(type="future_event_type", payload={"data": 123})
    assert e.type == "future_event_type"


# ── /feedback endpoint ────────────────────────────────────────────────────────


def test_feedback_thumbs_up(client):
    resp = client.post(
        "/feedback",
        json={"recommendation_id": "rec_fb1", "rating": 5, "label": "good"},
    )
    assert resp.status_code == 204


def test_feedback_thumbs_down(client):
    resp = client.post(
        "/feedback",
        json={"recommendation_id": "rec_fb2", "rating": 1, "label": "bad_strategy"},
    )
    assert resp.status_code == 204


def test_feedback_minimal_body(client):
    resp = client.post(
        "/feedback",
        json={"recommendation_id": "rec_fb3"},
    )
    assert resp.status_code == 204


def test_feedback_with_comment(client):
    resp = client.post(
        "/feedback",
        json={
            "recommendation_id": "rec_fb4",
            "rating": 3,
            "label": "unclear",
            "comment": "Not sure what to do with this.",
            "followed_plan": False,
        },
    )
    assert resp.status_code == 204


def test_feedback_invalid_label(client):
    resp = client.post(
        "/feedback",
        json={"recommendation_id": "rec_fb5", "label": "nonexistent_label"},
    )
    assert resp.status_code == 422


def test_feedback_rating_out_of_range(client):
    resp = client.post(
        "/feedback",
        json={"recommendation_id": "rec_fb6", "rating": 10},
    )
    assert resp.status_code == 422


def test_feedback_missing_recommendation_id(client):
    resp = client.post("/feedback", json={"rating": 5})
    assert resp.status_code == 422


def test_feedback_all_valid_labels(client):
    valid_labels = [
        "good",
        "bad_illegal",
        "bad_strategy",
        "bad_positioning",
        "bad_counter",
        "too_expensive",
        "unclear",
    ]
    for label in valid_labels:
        resp = client.post(
            "/feedback",
            json={"recommendation_id": f"rec_{label}", "label": label},
        )
        assert resp.status_code == 204, f"Label {label!r} should be valid"
