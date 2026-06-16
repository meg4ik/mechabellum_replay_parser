"""Tests for construction normalization (Phase 2)."""


from mechabellum_replay_parser.coach.constructions import normalize_construction
from mechabellum_replay_parser.coach.coordinates import CoordinateFrame
from mechabellum_replay_parser.coach.schemas import (
    ConstructionRole,
    ConstructionStatus,
    ConstructionType,
    ConstructionView,
    PlayerSide,
)


def _raw(
    ctype: str = "Supply Tower",
    cid: int = 1,
    x: int = 100,
    y: int = -270,
    status: str | None = None,
) -> dict:
    result: dict = {
        "type": ctype,
        "construction_id": cid,
        "index": 0,
        "position": {"x": x, "y": y},
    }
    if status is not None:
        result["status"] = status
    return result


# ── ID-based normalization ────────────────────────────────────────────────────


def test_id_1_is_supply_tower():
    c = normalize_construction({"construction_id": 1, "type": "Supply Tower"})
    assert c.type == ConstructionType.SUPPLY_TOWER
    assert c.role == ConstructionRole.ECONOMY


def test_id_2_is_command_tower():
    c = normalize_construction({"construction_id": 2, "type": "Command Tower"})
    assert c.type == ConstructionType.COMMAND_TOWER
    assert c.role == ConstructionRole.COMMAND


def test_id_3_is_research_tower():
    c = normalize_construction({"construction_id": 3, "type": "Research Tower"})
    assert c.type == ConstructionType.RESEARCH_TOWER
    assert c.role == ConstructionRole.RESEARCH


def test_unknown_id_stays_unknown():
    c = normalize_construction({"construction_id": 99, "type": "WeirdThing"})
    assert c.type == ConstructionType.UNKNOWN
    assert c.role == ConstructionRole.UNKNOWN


# ── String name normalization ─────────────────────────────────────────────────


def test_string_supply_tower_normalizes():
    c = normalize_construction({"type": "Supply Tower"})
    assert c.type == ConstructionType.SUPPLY_TOWER


def test_string_command_tower_normalizes():
    c = normalize_construction({"type": "Command Tower"})
    assert c.type == ConstructionType.COMMAND_TOWER


def test_string_research_tower_normalizes():
    c = normalize_construction({"type": "Research Tower"})
    assert c.type == ConstructionType.RESEARCH_TOWER


def test_unknown_string_stays_unknown():
    c = normalize_construction({"type": "MagicBuilding"})
    assert c.type == ConstructionType.UNKNOWN


# ── Status ────────────────────────────────────────────────────────────────────


def test_default_status_is_alive():
    c = normalize_construction({"type": "Supply Tower", "construction_id": 1})
    assert c.status == ConstructionStatus.ALIVE


def test_destroyed_status_parsed():
    c = normalize_construction(
        {"type": "Supply Tower", "construction_id": 1, "status": "destroyed"}
    )
    assert c.status == ConstructionStatus.DESTROYED


def test_no_status_field_defaults_alive():
    c = normalize_construction({"type": "Supply Tower"})
    assert c.status == ConstructionStatus.ALIVE


# ── Position ──────────────────────────────────────────────────────────────────


def test_position_preserved():
    c = normalize_construction(_raw(x=100, y=-270))
    assert c.position is not None
    assert c.position.x == 100
    assert c.position.y == -270


def test_no_position_is_none():
    c = normalize_construction({"type": "Supply Tower", "construction_id": 1})
    assert c.position is None


# ── raw_type preserved ────────────────────────────────────────────────────────


def test_raw_type_stored():
    c = normalize_construction({"type": "Supply Tower", "construction_id": 1})
    assert c.raw_type == "Supply Tower"


def test_raw_type_stored_for_unknown():
    c = normalize_construction({"type": "WeirdThing"})
    assert c.raw_type == "WeirdThing"


# ── position_label with CoordinateFrame ──────────────────────────────────────


def test_position_label_computed_with_frame():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    c = normalize_construction(_raw(x=0, y=-295), frame=frame)
    assert c.position_label == "center_back"


def test_position_label_none_without_frame():
    c = normalize_construction(_raw(x=0, y=-295))
    assert c.position_label is None


def test_position_label_none_when_no_position():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    c = normalize_construction({"type": "Supply Tower"}, frame=frame)
    assert c.position_label is None


# ── Returns ConstructionView ──────────────────────────────────────────────────


def test_returns_construction_view_instance():
    c = normalize_construction({"type": "Supply Tower", "construction_id": 1})
    assert isinstance(c, ConstructionView)


# ── StateView integration ─────────────────────────────────────────────────────


def test_state_view_contains_normalized_constructions(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    state = StateViewBuilder().build(parsed_replay, supply=100, player_name="Player1")
    assert len(state.my_state.constructions) == 1
    c = state.my_state.constructions[0]
    # conftest has construction_id=1 (Supply Tower) at (100, -270)
    assert c.type == ConstructionType.SUPPLY_TOWER
    assert c.role == ConstructionRole.ECONOMY
    assert c.status == ConstructionStatus.ALIVE


def test_state_view_construction_has_position_label(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    state = StateViewBuilder().build(parsed_replay, supply=100, player_name="Player1")
    c = state.my_state.constructions[0]
    # position (100, -270) with unit at (-40, -80) → NEGATIVE_Y frame
    assert c.position_label is not None
    assert "_" in c.position_label  # e.g. "right_center_back"


# ── UI serialization uses normalized type values ──────────────────────────────


def test_serialized_type_is_enum_value(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    state = StateViewBuilder().build(parsed_replay, supply=100, player_name="Player1")
    serialized = state.my_state.constructions[0].model_dump()
    assert serialized["type"] == "supply_tower"
    assert serialized["role"] == "economy"
    assert serialized["status"] == "alive"
