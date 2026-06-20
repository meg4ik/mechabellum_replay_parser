from __future__ import annotations

from .coordinates import CoordinateFrame
from .schemas import PlacementAction, PlacementIntent, Position, ResolvedPlacement, UnitView, Zone

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
        opponent_frame: CoordinateFrame | None = None,
    ) -> list[ResolvedPlacement]:
        occupied: set[tuple[int, int]] = set()
        if existing_units:
            for u in existing_units:
                if u.position:
                    occupied.add((u.position.x, u.position.y))

        unit_positions: dict[str, Position] = {}
        if existing_units:
            for u in existing_units:
                if u.position:
                    key = f"{u.name.lower()}_{u.index or 0}"
                    unit_positions[key] = u.position

        results: list[ResolvedPlacement] = []
        for intent in intents:
            if intent.action == PlacementAction.KEEP:
                key = f"{intent.unit.lower()}_{getattr(intent, '_unit_index', 0)}"
                current_pos = unit_positions.get(key)
                if not current_pos:
                    for k, v in unit_positions.items():
                        if k.startswith(intent.unit.lower() + "_"):
                            current_pos = v
                            break
                if current_pos:
                    results.append(
                        ResolvedPlacement(
                            unit=intent.unit,
                            action=intent.action,
                            x=current_pos.x,
                            y=current_pos.y,
                            lane=intent.lane,
                            depth=intent.depth,
                            zone=intent.zone,
                            purpose=intent.purpose,
                        )
                    )
                    continue

            target_frame = frame
            if intent.zone == Zone.OPPONENT and opponent_frame is not None:
                target_frame = opponent_frame

            base = target_frame.lane_depth_to_xy(intent.lane, intent.depth)
            pos = self._find_free(base, occupied, target_frame)
            occupied.add((pos.x, pos.y))
            results.append(
                ResolvedPlacement(
                    unit=intent.unit,
                    action=intent.action,
                    x=pos.x,
                    y=pos.y,
                    lane=intent.lane,
                    depth=intent.depth,
                    zone=intent.zone,
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
