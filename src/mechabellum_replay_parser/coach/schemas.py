from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel


# ── Coordinate enums ──────────────────────────────────────────────────────────


class PlayerSide(str, Enum):
    NEGATIVE_Y = "negative_y"
    POSITIVE_Y = "positive_y"


class Lane(str, Enum):
    LEFT = "left"
    LEFT_CENTER = "left_center"
    CENTER = "center"
    RIGHT_CENTER = "right_center"
    RIGHT = "right"


class Depth(str, Enum):
    FRONT = "front"
    MID_FRONT = "mid_front"
    MID = "mid"
    MID_BACK = "mid_back"
    BACK = "back"


# ── Placement models ──────────────────────────────────────────────────────────


class PlacementAction(str, Enum):
    KEEP = "keep"
    MOVE = "move"
    NEW = "new"


class PlacementAnchor(str, Enum):
    NONE = "none"
    BEHIND_CHAFF = "behind_chaff"
    PROTECT_TOWER = "protect_tower"
    PROTECT_BACKLINE = "protect_backline"
    FLANK_PRESSURE = "flank_pressure"
    CENTER_COVERAGE = "center_coverage"


class PlacementIntent(BaseModel):
    unit: str
    action: PlacementAction
    lane: Lane
    depth: Depth
    anchor: PlacementAnchor = PlacementAnchor.NONE
    purpose: str | None = None


class ResolvedPlacement(BaseModel):
    unit: str
    action: PlacementAction
    x: int
    y: int
    lane: Lane
    depth: Depth
    purpose: str | None = None


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


class ConstructionType(str, Enum):
    SUPPLY_TOWER = "supply_tower"
    COMMAND_TOWER = "command_tower"
    RESEARCH_TOWER = "research_tower"
    UNKNOWN = "unknown"


class ConstructionRole(str, Enum):
    ECONOMY = "economy"
    COMMAND = "command"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class ConstructionStatus(str, Enum):
    ALIVE = "alive"
    DESTROYED = "destroyed"
    UNKNOWN = "unknown"


class ConstructionView(BaseModel):
    type: ConstructionType = ConstructionType.UNKNOWN
    role: ConstructionRole = ConstructionRole.UNKNOWN
    status: ConstructionStatus = ConstructionStatus.ALIVE
    raw_type: str | None = None
    construction_id: int | None = None
    index: int | None = None
    position: Position | None = None
    position_label: str | None = None


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


# ── Legal actions ─────────────────────────────────────────────────────────────

ActionType = Literal[
    "buy_unit",
    "unlock_unit",
    "research_tech",
    "move_unit",
    "keep_unit",
    "use_skill",
    "build_construction",
    "skip",
]


class LegalAction(BaseModel):
    id: str
    type: ActionType
    cost: int = 0
    unit: str | None = None
    unit_index: int | None = None
    tech: str | None = None
    construction: str | None = None
    allowed_positions: list[dict] = []
    reason_tags: list[str] = []
    constraints: list[str] = []


class ActionGroup(BaseModel):
    id: str
    title: str
    purpose: str
    actions: list[LegalAction]
    total_cost: int
    addresses_threats: list[str]
    risks: list[str] = []


# ── Candidate plan ────────────────────────────────────────────────────────────


class CandidatePlan(BaseModel):
    id: str
    title: str
    action_ids: list[str]
    total_cost: int
    main_goal: str
    why_it_works: str
    risks: list[str]
    expected_enemy_response: list[str]
    placement: list[dict] = []
    placement_intents: list[PlacementIntent] = []
    confidence: float


# ── Validation ────────────────────────────────────────────────────────────────


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str


class PlanValidationResult(BaseModel):
    plan_id: str
    is_valid: bool
    issues: list[ValidationIssue]
    normalized_plan: CandidatePlan | None = None


# ── Judge output ─────────────────────────────────────────────────────────────


class RejectedPlan(BaseModel):
    plan_id: str
    reason: str


class JudgeOutput(BaseModel):
    best_plan_id: str
    confidence: float = 0.5
    main_reason: str
    why_not_others: list[RejectedPlan] = []
    final_actions: list[dict] = []
    placement: list[dict] = []
    watch_next_round: list[str] = []
    mistake_to_avoid: str = ""


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
    resolved_placements: list[ResolvedPlacement] = []
    risks: list[str] = []
    watch_next_round: list[str] = []
    coach_text: str = ""
    validation: PlanValidationResult | None = None
