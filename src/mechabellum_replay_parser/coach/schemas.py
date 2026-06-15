from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int


class UnitView(BaseModel):
    name: str
    unit_id: int | None = None
    index: int | None = None
    level: int | None = None
    exp: int | None = None
    rounds_survived: int | None = None
    position: Position | None = None
    equipment: str | None = None
    sell_supply: int | None = None
    rotate: bool | None = None
    active_techs: list[str] = []


class ConstructionView(BaseModel):
    type: str
    construction_id: int | None = None
    index: int | None = None
    position: Position | None = None
    status: Literal["alive", "destroyed", "unknown"] = "unknown"


class ShopView(BaseModel):
    unlocked: list[str] = []
    locked: list[str] = []
    buys_remaining: int | None = None
    unlocks_remaining: int | None = None


class PlayerRoundView(BaseModel):
    name: str
    hp: int | None = None
    supply: int | None = None
    army_value: int | None = None
    fight_outcome: str | None = None
    officers: list[str] = []
    commander_skills: list[dict] = []
    units: list[UnitView] = []
    constructions: list[ConstructionView] = []
    contraptions: list[dict] = []
    shop: ShopView | None = None


class RoundSummary(BaseModel):
    round: int
    my_outcome: str | None = None
    enemy_outcome: str | None = None
    my_army_value: int | None = None
    enemy_army_value: int | None = None
    important_changes: list[str] = []


class StrategicMemory(BaseModel):
    enemy_plan_read: str | None = None
    my_plan_read: str | None = None
    critical_events: list[str] = []
    committed_investments: list[str] = []
    do_not_forget: list[str] = []


class StateView(BaseModel):
    match_mode: str | None = None
    round: int
    player_name: str
    enemy_names: list[str]
    my_supply: int | None = None
    my_state: PlayerRoundView
    enemy_states: list[PlayerRoundView]
    recent_rounds: list[RoundSummary]
    strategic_memory: StrategicMemory


# ── TacticalFeatures ──────────────────────────────────────────────────────────

class ThreatSignal(BaseModel):
    key: str
    severity: float
    source_units: list[str] = []
    explanation: str
    my_answer: Literal["none", "weak", "medium", "good", "unknown"] = "unknown"


class TacticalFeatures(BaseModel):
    threats: list[ThreatSignal]
    my_weaknesses: list[str]
    enemy_weaknesses: list[str]
    tempo_state: Literal["ahead", "even", "behind", "unknown"]
    board_posture: Literal["aggro", "standard", "defensive", "unknown"]
    tower_notes: list[str]
    likely_enemy_continuation: list[str]
    priority_questions: list[str]


# ── CoachRecommendation ───────────────────────────────────────────────────────

class PlannedAction(BaseModel):
    type: str
    unit: str | None = None
    tech: str | None = None
    x: int | None = None
    y: int | None = None
    reason: str = ""


class CoachRecommendation(BaseModel):
    summary: str
    confidence: float = 0.0
    main_threats: list[str] = []
    actions: list[PlannedAction] = []
    placement: list[dict] = []
    risks: list[str] = []
    watch_next_round: list[str] = []
    coach_text: str = ""
