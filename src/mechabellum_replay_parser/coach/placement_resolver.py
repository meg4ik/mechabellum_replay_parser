from __future__ import annotations

from .coordinates import CoordinateFrame
from .schemas import PlacementIntent, Position, ResolvedPlacement, UnitView

_COLLISION_OFFSETS: list[tuple[int, int]] = [
    (0, 0),
    (-35, 0),
    (35, 0),
    (0, 35),
    (0, -35),
    (-70, 0),
    (70, 0),
]


class PlacementResolver:
    def resolve(
        self,
        intents: list[PlacementIntent],
        frame: CoordinateFrame,
        existing_units: list[UnitView] | None = None,
    ) -> list[ResolvedPlacement]:
        occupied: set[tuple[int, int]] = set()
        if existing_units:
            for u in existing_units:
                if u.position:
                    occupied.add((u.position.x, u.position.y))

        results: list[ResolvedPlacement] = []
        for intent in intents:
            base = frame.lane_depth_to_xy(intent.lane, intent.depth)
            pos = self._find_free(base, occupied, frame)
            occupied.add((pos.x, pos.y))
            results.append(
                ResolvedPlacement(
                    unit=intent.unit,
                    action=intent.action,
                    x=pos.x,
                    y=pos.y,
                    lane=intent.lane,
                    depth=intent.depth,
                    purpose=intent.purpose,
                )
            )
        return results

    def _find_free(
        self,
        base: Position,
        occupied: set[tuple[int, int]],
        frame: CoordinateFrame,
    ) -> Position:
        for dx, dy in _COLLISION_OFFSETS:
            candidate = frame.clamp(Position(x=base.x + dx, y=base.y + dy))
            if (candidate.x, candidate.y) not in occupied:
                return candidate
        return frame.clamp(base)
