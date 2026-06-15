from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex}"


def _new_rec_id() -> str:
    return f"rec_{uuid.uuid4().hex}"


class UIEvent(BaseModel):
    event_id: str = Field(default_factory=_new_event_id)
    type: str
    created_at: str = Field(default_factory=_now_iso)
    payload: dict


class SupplyRequestPayload(BaseModel):
    recommendation_id: str
    round: int
    player_name: str
    timeout_seconds: int | None = None


class SupplyResponseBody(BaseModel):
    recommendation_id: str
    supply: int | None
    cancelled: bool = False


class RecommendationReadyPayload(BaseModel):
    recommendation_id: str
    round: int
    player_name: str
    summary: str
    current_units: list[dict]
    constructions: list[dict]
    placement: list[dict]
    coach_text: str
