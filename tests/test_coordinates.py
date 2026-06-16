"""Tests for CoordinateFrame."""

from mechabellum_replay_parser.coach.coordinates import CoordinateFrame
from mechabellum_replay_parser.coach.schemas import (
    ConstructionView,
    Depth,
    Lane,
    PlayerSide,
    Position,
    UnitView,
)


def _unit(y: int) -> UnitView:
    return UnitView(name="crawler", position=Position(x=0, y=y))


def _construction(y: int) -> ConstructionView:
    return ConstructionView(type="supply_tower", position=Position(x=100, y=y))


# ── Side detection ────────────────────────────────────────────────────────────


def test_negative_y_detected_from_units():
    frame = CoordinateFrame.from_units_and_constructions([_unit(-80)], [])
    assert frame.side == PlayerSide.NEGATIVE_Y


def test_positive_y_detected_from_units():
    frame = CoordinateFrame.from_units_and_constructions([_unit(80)], [])
    assert frame.side == PlayerSide.POSITIVE_Y


def test_negative_y_detected_from_constructions():
    frame = CoordinateFrame.from_units_and_constructions([], [_construction(-270)])
    assert frame.side == PlayerSide.NEGATIVE_Y


def test_no_units_defaults_to_negative_y():
    frame = CoordinateFrame.from_units_and_constructions([], [])
    assert frame.side == PlayerSide.NEGATIVE_Y


def test_units_without_positions_default_to_negative_y():
    units = [UnitView(name="crawler")]  # no position
    frame = CoordinateFrame.from_units_and_constructions(units, [])
    assert frame.side == PlayerSide.NEGATIVE_Y


# ── Bounds ────────────────────────────────────────────────────────────────────


def test_negative_y_front_back():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.front_y == -10
    assert frame.back_y == -310


def test_positive_y_front_back():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    assert frame.front_y == 10
    assert frame.back_y == 310


def test_in_bounds_negative_y():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.is_in_bounds(Position(x=0, y=-100))
    assert frame.is_in_bounds(Position(x=-290, y=-295))
    assert frame.is_in_bounds(Position(x=290, y=-50))


def test_out_of_bounds_x_negative_y():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert not frame.is_in_bounds(Position(x=310, y=-100))
    assert not frame.is_in_bounds(Position(x=-310, y=-100))


def test_out_of_bounds_y_negative_y():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert not frame.is_in_bounds(Position(x=0, y=0))
    assert not frame.is_in_bounds(Position(x=0, y=-315))


def test_in_bounds_positive_y():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    assert frame.is_in_bounds(Position(x=0, y=100))
    assert frame.is_in_bounds(Position(x=0, y=50))
    assert frame.is_in_bounds(Position(x=0, y=295))


def test_out_of_bounds_positive_y():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    assert not frame.is_in_bounds(Position(x=0, y=0))
    assert not frame.is_in_bounds(Position(x=0, y=315))


# ── Clamp ─────────────────────────────────────────────────────────────────────


def test_clamp_x_too_large():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.clamp(Position(x=999, y=-100)).x == 300


def test_clamp_x_too_small():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.clamp(Position(x=-999, y=-100)).x == -300


def test_clamp_y_above_front():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    # y=0 is above front_y=-10 → clamps to -10
    assert frame.clamp(Position(x=0, y=0)).y == -10


def test_clamp_y_below_back():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    # y=-400 is below back_y=-310 → clamps to -310
    assert frame.clamp(Position(x=0, y=-400)).y == -310


def test_clamp_positive_y_below_front():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    # y=0 is below front_y=10 → clamps to 10
    assert frame.clamp(Position(x=0, y=0)).y == 10


def test_clamp_already_in_bounds():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    pos = Position(x=0, y=-100)
    assert frame.clamp(pos) == pos


# ── Lane/depth mapping ────────────────────────────────────────────────────────


def test_lane_depth_negative_y_center_front():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    pos = frame.lane_depth_to_xy(Lane.CENTER, Depth.FRONT)
    assert pos.x == 0
    assert pos.y == -10


def test_lane_depth_negative_y_center_back():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    pos = frame.lane_depth_to_xy(Lane.CENTER, Depth.BACK)
    assert pos.x == 0
    assert pos.y == -310


def test_lane_depth_positive_y_center_front():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    pos = frame.lane_depth_to_xy(Lane.CENTER, Depth.FRONT)
    assert pos.x == 0
    assert pos.y == 10


def test_lane_depth_positive_y_center_back():
    frame = CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)
    pos = frame.lane_depth_to_xy(Lane.CENTER, Depth.BACK)
    assert pos.x == 0
    assert pos.y == 310


def test_lane_x_values():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.lane_depth_to_xy(Lane.LEFT, Depth.FRONT).x == -228
    assert frame.lane_depth_to_xy(Lane.LEFT_CENTER, Depth.FRONT).x == -114
    assert frame.lane_depth_to_xy(Lane.CENTER, Depth.FRONT).x == 0
    assert frame.lane_depth_to_xy(Lane.RIGHT_CENTER, Depth.FRONT).x == 114
    assert frame.lane_depth_to_xy(Lane.RIGHT, Depth.FRONT).x == 228


def test_all_lane_depth_combos_always_in_bounds():
    for side in PlayerSide:
        frame = CoordinateFrame.for_side(side)
        for lane in Lane:
            for depth in Depth:
                pos = frame.lane_depth_to_xy(lane, depth)
                assert frame.is_in_bounds(pos), (
                    f"{side} {lane} {depth} -> {pos} out of bounds"
                )


# ── position_to_label ─────────────────────────────────────────────────────────


def test_position_to_label_center_front():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    # front_y=-10, mid_front_y≈-85; midpoint≈-47.5, so -30 is clearly in front zone
    assert frame.position_to_label(Position(x=0, y=-30)) == "center_front"


def test_position_to_label_left_back():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    assert frame.position_to_label(Position(x=-228, y=-295)) == "left_back"


def test_position_to_label_right_mid():
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    pos = frame.lane_depth_to_xy(Lane.RIGHT, Depth.MID)
    assert frame.position_to_label(pos) == "right_mid"


def test_position_to_label_roundtrip():
    """lane_depth_to_xy then position_to_label should give back lane_depth."""
    frame = CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)
    for lane in Lane:
        for depth in Depth:
            pos = frame.lane_depth_to_xy(lane, depth)
            label = frame.position_to_label(pos)
            assert label == f"{lane.value}_{depth.value}", (
                f"{lane} {depth}: expected {lane.value}_{depth.value}, got {label}"
            )
