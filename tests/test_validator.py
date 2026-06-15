"""Tests for PlanValidator."""
import pytest

from mechabellum_replay_parser.coach.schemas import (
    PlayerRoundView,
    PlanValidationResult,
    ShopView,
    StateView,
    StrategicMemory,
    UnitView,
)
from mechabellum_replay_parser.coach.validator import PlanValidator


def _make_state(
    unlocked: list[str] = (),
    locked: list[str] = (),
    buys_remaining: int = 4,
    supply: int | None = 500,
    units: list[UnitView] = (),
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=2,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=supply,
        my_state=PlayerRoundView(
            name="Me",
            army_value=500,
            units=list(units),
            shop=ShopView(
                unlocked=list(unlocked),
                locked=list(locked),
                buys_remaining=buys_remaining,
            ),
        ),
        enemy_states=[PlayerRoundView(name="Enemy")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _entry(unit: str, action: str = "keep", x: int = 0, y: int = -100) -> dict:
    return {"unit": unit, "x": x, "y": y, "action": action}


@pytest.fixture
def validator():
    return PlanValidator()


# ── Happy path ────────────────────────────────────────────────────────────────

def test_valid_empty_placement(validator):
    state = _make_state()
    result = validator.validate_placement([], state)
    assert isinstance(result, PlanValidationResult)
    assert result.is_valid is True
    assert result.issues == []


def test_valid_keep_existing_unit(validator):
    state = _make_state(units=[UnitView(name="crawler")])
    result = validator.validate_placement([_entry("crawler", "keep")], state)
    assert result.is_valid is True


def test_valid_buy_unlocked_unit(validator):
    state = _make_state(unlocked=["crawler"], buys_remaining=4, supply=200)
    result = validator.validate_placement([_entry("crawler", "new")], state)
    assert result.is_valid is True


def test_valid_move_existing_unit(validator):
    state = _make_state(units=[UnitView(name="rhino")])
    result = validator.validate_placement([_entry("rhino", "move", x=50, y=-100)], state)
    assert result.is_valid is True


# ── Too many buys ─────────────────────────────────────────────────────────────

def test_too_many_buys_error(validator):
    state = _make_state(unlocked=["crawler"], buys_remaining=1, supply=9999)
    placement = [_entry("crawler", "new"), _entry("crawler", "new")]
    result = validator.validate_placement(placement, state)
    assert result.is_valid is False
    codes = [i.code for i in result.issues]
    assert "too_many_buys" in codes


def test_buys_exactly_at_limit_is_valid(validator):
    state = _make_state(unlocked=["crawler"], buys_remaining=2, supply=9999)
    placement = [_entry("crawler", "new"), _entry("crawler", "new")]
    result = validator.validate_placement(placement, state)
    errors = [i for i in result.issues if i.code == "too_many_buys"]
    assert errors == []


def test_buys_not_checked_when_buys_remaining_none(validator):
    """If buys_remaining is None (unknown), skip the check."""
    state = StateView(
        match_mode="VS_1_1",
        round=2,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=9999,
        my_state=PlayerRoundView(
            name="Me",
            shop=ShopView(unlocked=["crawler"], buys_remaining=None),
        ),
        enemy_states=[PlayerRoundView(name="Enemy")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )
    placement = [_entry("crawler", "new")] * 10
    result = validator.validate_placement(placement, state)
    codes = [i.code for i in result.issues]
    assert "too_many_buys" not in codes


# ── Unit not unlocked ─────────────────────────────────────────────────────────

def test_buying_locked_unit_is_error(validator):
    state = _make_state(unlocked=[], locked=["phoenix"], buys_remaining=4, supply=9999)
    result = validator.validate_placement([_entry("phoenix", "new")], state)
    assert result.is_valid is False
    codes = [i.code for i in result.issues]
    assert "unit_not_unlocked" in codes


def test_buying_unlocked_unit_no_error(validator):
    state = _make_state(unlocked=["phoenix"], buys_remaining=4, supply=9999)
    result = validator.validate_placement([_entry("phoenix", "new")], state)
    codes = [i.code for i in result.issues]
    assert "unit_not_unlocked" not in codes


# ── Unit not found (keep/move non-existent) ───────────────────────────────────

def test_keep_nonexistent_unit_is_warning(validator):
    state = _make_state(units=[])
    result = validator.validate_placement([_entry("phantom ray", "keep")], state)
    codes = [i.code for i in result.issues]
    assert "unit_not_found" in codes
    sev = next(i.severity for i in result.issues if i.code == "unit_not_found")
    assert sev == "warning"


def test_keep_nonexistent_is_warning_not_error(validator):
    """unit_not_found is a warning, not an error — plan stays valid."""
    state = _make_state(units=[])
    result = validator.validate_placement([_entry("phantom ray", "keep")], state)
    assert result.is_valid is True  # only errors block validity


def test_move_nonexistent_unit_is_warning(validator):
    state = _make_state(units=[])
    result = validator.validate_placement([_entry("fortress", "move")], state)
    codes = [i.code for i in result.issues]
    assert "unit_not_found" in codes


def test_keep_same_unit_twice_when_only_one_in_army(validator):
    """Keeping the same unit name twice when only 1 is in army → warning on second."""
    state = _make_state(units=[UnitView(name="crawler")])
    placement = [_entry("crawler", "keep"), _entry("crawler", "keep")]
    result = validator.validate_placement(placement, state)
    codes = [i.code for i in result.issues]
    assert "unit_not_found" in codes


# ── Coordinate bounds ─────────────────────────────────────────────────────────

def test_x_out_of_bounds_is_error(validator):
    state = _make_state(units=[UnitView(name="crawler")])
    result = validator.validate_placement([_entry("crawler", "keep", x=999, y=-100)], state)
    codes = [i.code for i in result.issues]
    assert "out_of_bounds_x" in codes
    assert result.is_valid is False


def test_y_out_of_bounds_is_error(validator):
    state = _make_state(units=[UnitView(name="crawler")])
    result = validator.validate_placement([_entry("crawler", "keep", x=0, y=999)], state)
    codes = [i.code for i in result.issues]
    assert "out_of_bounds_y" in codes
    assert result.is_valid is False


def test_valid_corner_coordinates(validator):
    state = _make_state(units=[UnitView(name="crawler")])
    result = validator.validate_placement([_entry("crawler", "keep", x=-285, y=-295)], state)
    bound_codes = [i.code for i in result.issues if "out_of_bounds" in i.code]
    assert bound_codes == []


def test_valid_max_coordinates(validator):
    state = _make_state(units=[UnitView(name="crawler")])
    result = validator.validate_placement([_entry("crawler", "keep", x=285, y=-45)], state)
    bound_codes = [i.code for i in result.issues if "out_of_bounds" in i.code]
    assert bound_codes == []


# ── Supply budget warning ─────────────────────────────────────────────────────

def test_supply_overspend_is_warning(validator):
    # fortress costs 400; supply = 100
    state = _make_state(unlocked=["fortress"], buys_remaining=4, supply=100)
    # Still technically in unlocked so no unit_not_unlocked, but budget exceeded
    result = validator.validate_placement([_entry("fortress", "new")], state)
    codes = [i.code for i in result.issues]
    assert "supply_overspend" in codes
    sev = next(i.severity for i in result.issues if i.code == "supply_overspend")
    assert sev == "warning"


def test_no_supply_overspend_when_supply_none(validator):
    """If supply is None (not entered), skip budget check."""
    state = _make_state(unlocked=["fortress"], buys_remaining=4, supply=None)
    result = validator.validate_placement([_entry("fortress", "new")], state)
    codes = [i.code for i in result.issues]
    assert "supply_overspend" not in codes


def test_unknown_action_is_warning(validator):
    state = _make_state()
    result = validator.validate_placement([_entry("crawler", "teleport")], state)
    codes = [i.code for i in result.issues]
    assert "unknown_action" in codes


# ── Integration with parsed_replay fixture ────────────────────────────────────

def test_validate_valid_keep_from_parsed_replay(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    builder = StateViewBuilder()
    validator = PlanValidator()
    state = builder.build(parsed_replay, supply=200, player_name="Player1")

    # Player1 has 1 crawler at (-40, -80) — keeping it is valid
    placement = [{"unit": "crawler", "x": -40, "y": -80, "action": "keep"}]
    result = validator.validate_placement(placement, state)
    assert result.is_valid is True
    assert not any(i.code == "unit_not_found" for i in result.issues)
