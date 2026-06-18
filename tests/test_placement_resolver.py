"""Tests for PlacementResolver."""

import pytest

from mechabellum_replay_parser.coach.coordinates import CoordinateFrame
from mechabellum_replay_parser.coach.placement_resolver import PlacementResolver
from mechabellum_replay_parser.coach.schemas import (
    Depth,
    Lane,
    PlacementAction,
    PlacementIntent,
    PlayerSide,
    Position,
    ResolvedPlacement,
    UnitView,
    Zone,
)


@pytest.fixture
def frame():
    return CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)


@pytest.fixture
def resolver():
    return PlacementResolver()


def _intent(
    unit: str = "mustang",
    action: PlacementAction = PlacementAction.NEW,
    lane: Lane = Lane.CENTER,
    depth: Depth = Depth.BACK,
    purpose: str | None = None,
) -> PlacementIntent:
    return PlacementIntent(
        unit=unit, action=action, lane=lane, depth=depth, purpose=purpose
    )


# ── Basic resolution ──────────────────────────────────────────────────────────


def test_resolve_single_intent(resolver, frame):
    results = resolver.resolve([_intent("mustang")], frame)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ResolvedPlacement)
    assert r.unit == "mustang"
    assert r.action == PlacementAction.NEW
    assert r.lane == Lane.CENTER
    assert r.depth == Depth.BACK
    assert frame.is_in_bounds(Position(x=r.x, y=r.y))


def test_resolve_empty_intents(resolver, frame):
    assert resolver.resolve([], frame) == []


def test_resolve_preserves_purpose(resolver, frame):
    results = resolver.resolve([_intent(purpose="anti_air_cover")], frame)
    assert results[0].purpose == "anti_air_cover"


def test_resolved_x_y_always_in_bounds(resolver, frame):
    intents = [
        _intent(f"unit_{lane.value}_{depth.value}", lane=lane, depth=depth)
        for lane in Lane
        for depth in Depth
    ]
    for r in resolver.resolve(intents, frame):
        pos = Position(x=r.x, y=r.y)
        assert frame.is_in_bounds(pos), f"{r.unit} -> ({r.x}, {r.y}) out of bounds"


# ── Collision avoidance ───────────────────────────────────────────────────────


def test_collision_avoidance_two_same_lane_depth(resolver, frame):
    intents = [_intent("mustang"), _intent("arclight")]
    results = resolver.resolve(intents, frame)
    assert len(results) == 2
    assert (results[0].x, results[0].y) != (results[1].x, results[1].y)


def test_collision_avoidance_with_existing_units(resolver, frame):
    # pre-occupy the center_back position
    existing = [UnitView(name="crawler", position=Position(x=0, y=-295))]
    results = resolver.resolve(
        [_intent("mustang", lane=Lane.CENTER, depth=Depth.BACK)],
        frame,
        existing_units=existing,
    )
    assert len(results) == 1
    r = results[0]
    assert (r.x, r.y) != (0, -295)
    assert frame.is_in_bounds(Position(x=r.x, y=r.y))


def test_multiple_intents_all_get_unique_positions(resolver, frame):
    intents = [_intent(f"unit_{i}") for i in range(5)]
    results = resolver.resolve(intents, frame)
    positions = [(r.x, r.y) for r in results]
    assert len(set(positions)) == len(positions)


def test_existing_units_without_position_ignored(resolver, frame):
    existing = [UnitView(name="crawler")]  # no position — should not crash
    results = resolver.resolve([_intent("mustang")], frame, existing_units=existing)
    assert len(results) == 1


# ── Positive-Y side ───────────────────────────────────────────────────────────


def test_resolve_positive_y_in_bounds():
    frame_pos = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    results = PlacementResolver().resolve([_intent("mustang")], frame_pos)
    r = results[0]
    assert frame_pos.is_in_bounds(Position(x=r.x, y=r.y))
    assert r.y > 0


# ── Validator and resolver use same frame ─────────────────────────────────────


def test_resolved_placement_passes_validator_bounds():
    """Resolved positions must pass the validator's bounds check (same CoordinateFrame)."""
    from mechabellum_replay_parser.coach.schemas import (
        PlayerRoundView,
        ShopView,
        StateView,
        StrategicMemory,
    )
    from mechabellum_replay_parser.coach.validator import PlanValidator

    frame_neg = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    resolver = PlacementResolver()
    results = resolver.resolve(
        [_intent("mustang", PlacementAction.NEW, Lane.CENTER, Depth.BACK)],
        frame_neg,
    )
    r = results[0]
    placement = [{"unit": r.unit, "x": r.x, "y": r.y, "action": r.action.value}]

    state = StateView(
        round=2,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=9999,
        my_state=PlayerRoundView(
            name="Me",
            shop=ShopView(unlocked=["mustang"], buys_remaining=4),
            units=[UnitView(name="placeholder", position=Position(x=0, y=-80))],
        ),
        enemy_states=[PlayerRoundView(name="Enemy")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )
    result = PlanValidator().validate_placement(placement, state)
    bound_issues = [i for i in result.issues if "out_of_bounds" in i.code]
    assert bound_issues == []


# ── Opponent zone routing ────────────────────────────────────────────────────


def test_opponent_zone_intent_resolves_to_positive_y(resolver, frame):
    opp_frame = frame.opponent_frame()
    intent = PlacementIntent(
        unit="wasp", action=PlacementAction.NEW,
        lane=Lane.LEFT, depth=Depth.FRONT, zone=Zone.OPPONENT,
    )
    results = resolver.resolve([intent], frame, opponent_frame=opp_frame)
    r = results[0]
    assert r.y > 0
    assert r.zone == Zone.OPPONENT
    assert opp_frame.is_in_bounds(Position(x=r.x, y=r.y))


def test_own_zone_intent_stays_negative_y(resolver, frame):
    opp_frame = frame.opponent_frame()
    intent = PlacementIntent(
        unit="crawler", action=PlacementAction.NEW,
        lane=Lane.CENTER, depth=Depth.BACK, zone=Zone.OWN,
    )
    results = resolver.resolve([intent], frame, opponent_frame=opp_frame)
    r = results[0]
    assert r.y < 0
    assert r.zone == Zone.OWN


def test_mixed_zones_resolve_correctly(resolver, frame):
    opp_frame = frame.opponent_frame()
    intents = [
        PlacementIntent(
            unit="crawler", action=PlacementAction.NEW,
            lane=Lane.CENTER, depth=Depth.BACK, zone=Zone.OWN,
        ),
        PlacementIntent(
            unit="wasp", action=PlacementAction.NEW,
            lane=Lane.LEFT, depth=Depth.FRONT, zone=Zone.OPPONENT,
        ),
    ]
    results = resolver.resolve(intents, frame, opponent_frame=opp_frame)
    assert results[0].y < 0
    assert results[0].zone == Zone.OWN
    assert results[1].y > 0
    assert results[1].zone == Zone.OPPONENT


def test_opponent_zone_without_frame_falls_back(resolver, frame):
    intent = PlacementIntent(
        unit="wasp", action=PlacementAction.NEW,
        lane=Lane.LEFT, depth=Depth.FRONT, zone=Zone.OPPONENT,
    )
    results = resolver.resolve([intent], frame, opponent_frame=None)
    r = results[0]
    assert r.y < 0  # falls back to own frame
