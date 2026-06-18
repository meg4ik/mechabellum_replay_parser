from __future__ import annotations

from pydantic import BaseModel

from .schemas import ConstructionView, Depth, Lane, PlayerSide, Position, UnitView

_LANE_X: dict[Lane, int] = {
    Lane.LEFT: -228,
    Lane.LEFT_CENTER: -114,
    Lane.CENTER: 0,
    Lane.RIGHT_CENTER: 114,
    Lane.RIGHT: 228,
}

_DEPTHS = [Depth.FRONT, Depth.MID_FRONT, Depth.MID, Depth.MID_BACK, Depth.BACK]


class CoordinateFrame(BaseModel):
    side: PlayerSide
    x_min: int = -300
    x_max: int = 300
    front_y: int
    back_y: int

    @classmethod
    def for_side(cls, side: PlayerSide) -> CoordinateFrame:
        if side == PlayerSide.NEGATIVE_Y:
            return cls(side=side, front_y=-10, back_y=-310)
        return cls(side=side, front_y=10, back_y=310)

    @classmethod
    def from_units_and_constructions(
        cls,
        units: list[UnitView],
        constructions: list[ConstructionView],
    ) -> CoordinateFrame:
        ys = [u.position.y for u in units if u.position]
        ys += [c.position.y for c in constructions if c.position]
        if not ys:
            return cls.for_side(PlayerSide.NEGATIVE_Y)
        avg_y = sum(ys) / len(ys)
        side = PlayerSide.NEGATIVE_Y if avg_y <= 0 else PlayerSide.POSITIVE_Y
        return cls.for_side(side)

    def opponent_frame(self) -> CoordinateFrame:
        opp_side = (
            PlayerSide.POSITIVE_Y
            if self.side == PlayerSide.NEGATIVE_Y
            else PlayerSide.NEGATIVE_Y
        )
        return CoordinateFrame.for_side(opp_side)

    def clamp(self, position: Position) -> Position:
        y_lo = min(self.front_y, self.back_y)
        y_hi = max(self.front_y, self.back_y)
        return Position(
            x=max(self.x_min, min(self.x_max, position.x)),
            y=max(y_lo, min(y_hi, position.y)),
        )

    def is_in_bounds(self, position: Position) -> bool:
        y_lo = min(self.front_y, self.back_y)
        y_hi = max(self.front_y, self.back_y)
        return self.x_min <= position.x <= self.x_max and y_lo <= position.y <= y_hi

    def lane_depth_to_xy(self, lane: Lane, depth: Depth) -> Position:
        x = _LANE_X[lane]
        idx = _DEPTHS.index(depth)
        t = idx / (len(_DEPTHS) - 1)
        y = round(self.front_y + t * (self.back_y - self.front_y))
        return Position(x=x, y=y)

    def position_to_label(self, position: Position) -> str:
        nearest_lane = min(_LANE_X, key=lambda lane: abs(_LANE_X[lane] - position.x))
        nearest_depth = min(
            _DEPTHS,
            key=lambda d: abs(self.lane_depth_to_xy(nearest_lane, d).y - position.y),
        )
        return f"{nearest_lane.value}_{nearest_depth.value}"
