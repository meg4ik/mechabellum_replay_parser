from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .coordinates import CoordinateFrame
from .influence_schemas import (
    InfluenceGridSpec,
    MapZone,
    ZoneInfluenceSummary,
)
from .schemas import PlayerSide, StateView, UnitView
from .unit_stats import ResolvedUnitStats, UnitStatsResolver

_DEFAULT_WIDTH = 30
_DEFAULT_HEIGHT = 20
_DEFAULT_SOFTNESS = 18.0
_DURABILITY_RANGE = 40.0
_DURABILITY_SOFTNESS = 12.0
_ARTILLERY_FACTOR = 0.7
_EPSILON = 1e-9

_ZONE_COLS = 3
_ZONE_ROWS = 3

_ZONE_GRID: list[list[MapZone]] = [
    [MapZone.LEFT_FRONT, MapZone.CENTER_FRONT, MapZone.RIGHT_FRONT],
    [MapZone.LEFT_MID, MapZone.CENTER_MID, MapZone.RIGHT_MID],
    [MapZone.LEFT_BACK, MapZone.CENTER_BACK, MapZone.RIGHT_BACK],
]


@dataclass
class InfluenceMapArrays:
    my_ground: np.ndarray
    enemy_ground: np.ndarray
    my_air: np.ndarray
    enemy_air: np.ndarray
    my_anti_chaff: np.ndarray
    enemy_anti_chaff: np.ndarray
    my_anti_heavy: np.ndarray
    enemy_anti_heavy: np.ndarray
    my_artillery: np.ndarray
    enemy_artillery: np.ndarray
    my_durability: np.ndarray
    enemy_durability: np.ndarray


@dataclass
class InfluenceMapResult:
    grid: InfluenceGridSpec
    arrays: InfluenceMapArrays
    zones: list[ZoneInfluenceSummary] = field(default_factory=list)


def _sigmoid(
    distance: np.ndarray, effective_range: float, softness: float
) -> np.ndarray:
    return 1.0 / (1.0 + np.exp((distance - effective_range) / softness))


def _normalize(arr: np.ndarray) -> np.ndarray:
    mx = arr.max()
    if mx < _EPSILON:
        return np.zeros_like(arr)
    return arr / mx


class InfluenceMapBuilder:
    def __init__(
        self,
        unit_stats_resolver: UnitStatsResolver | None = None,
        grid_width: int = _DEFAULT_WIDTH,
        grid_height: int = _DEFAULT_HEIGHT,
        softness: float = _DEFAULT_SOFTNESS,
    ) -> None:
        self._resolver = unit_stats_resolver or UnitStatsResolver()
        self._width = grid_width
        self._height = grid_height
        self._softness = softness

    def build(self, state: StateView, frame: CoordinateFrame) -> InfluenceMapResult:
        opp = frame.opponent_frame()
        y_lo = min(frame.front_y, frame.back_y, opp.front_y, opp.back_y)
        y_hi = max(frame.front_y, frame.back_y, opp.front_y, opp.back_y)

        grid_spec = InfluenceGridSpec(
            x_min=float(frame.x_min),
            x_max=float(frame.x_max),
            y_front=float(frame.front_y),
            y_back=float(frame.back_y),
            width=self._width,
            height=self._height,
            player_side=frame.side.value,
        )

        xs = np.linspace(frame.x_min, frame.x_max, self._width)
        ys = np.linspace(y_lo, y_hi, self._height)
        grid_x, grid_y = np.meshgrid(xs, ys)

        shape = (self._height, self._width)
        arrays = InfluenceMapArrays(
            my_ground=np.zeros(shape),
            enemy_ground=np.zeros(shape),
            my_air=np.zeros(shape),
            enemy_air=np.zeros(shape),
            my_anti_chaff=np.zeros(shape),
            enemy_anti_chaff=np.zeros(shape),
            my_anti_heavy=np.zeros(shape),
            enemy_anti_heavy=np.zeros(shape),
            my_artillery=np.zeros(shape),
            enemy_artillery=np.zeros(shape),
            my_durability=np.zeros(shape),
            enemy_durability=np.zeros(shape),
        )

        my_techs = self._collect_techs(state.my_state.units)
        self._stamp_units(
            state.my_state.units,
            my_techs,
            grid_x,
            grid_y,
            arrays,
            is_mine=True,
        )

        for enemy in state.enemy_states:
            enemy_techs = self._collect_techs(enemy.units)
            self._stamp_units(
                enemy.units,
                enemy_techs,
                grid_x,
                grid_y,
                arrays,
                is_mine=False,
            )

        zones = self._aggregate_zones(arrays, frame)

        return InfluenceMapResult(grid=grid_spec, arrays=arrays, zones=zones)

    def _collect_techs(self, units: list[UnitView]) -> list[dict]:
        techs: list[dict] = []
        for u in units:
            for t in u.active_techs:
                if isinstance(t, str):
                    techs.append({"unit": u.name, "tech": t})
                elif isinstance(t, dict):
                    techs.append(t)
        return techs

    def _stamp_units(
        self,
        units: list[UnitView],
        techs: list[dict],
        grid_x: np.ndarray,
        grid_y: np.ndarray,
        arrays: InfluenceMapArrays,
        is_mine: bool,
    ) -> None:
        for unit in units:
            if not unit.position:
                continue
            stats = self._resolver.resolve_unit(unit, active_techs=techs)
            self._stamp_single(
                stats,
                float(unit.position.x),
                float(unit.position.y),
                grid_x,
                grid_y,
                arrays,
                is_mine,
            )

    def _stamp_single(
        self,
        stats: ResolvedUnitStats,
        ux: float,
        uy: float,
        grid_x: np.ndarray,
        grid_y: np.ndarray,
        arrays: InfluenceMapArrays,
        is_mine: bool,
    ) -> None:
        distance = np.sqrt((grid_x - ux) ** 2 + (grid_y - uy) ** 2)
        range_factor = _sigmoid(distance, stats.effective_range, self._softness)

        ground_inf = stats.effective_dps_ground * range_factor
        air_inf = stats.effective_dps_air * range_factor
        anti_chaff_inf = (
            stats.effective_dps_ground * stats.anti_chaff_score * range_factor
        )
        anti_heavy_inf = (
            stats.effective_dps_ground * stats.anti_heavy_score * range_factor
        )

        durability_factor = _sigmoid(distance, _DURABILITY_RANGE, _DURABILITY_SOFTNESS)
        durability_inf = stats.effective_hp * durability_factor

        is_artillery = "artillery" in stats.tags
        artillery_inf = (
            stats.effective_dps_ground * range_factor * _ARTILLERY_FACTOR
            if is_artillery
            else None
        )

        if is_mine:
            arrays.my_ground += ground_inf
            arrays.my_air += air_inf
            arrays.my_anti_chaff += anti_chaff_inf
            arrays.my_anti_heavy += anti_heavy_inf
            arrays.my_durability += durability_inf
            if artillery_inf is not None:
                arrays.my_artillery += artillery_inf
        else:
            arrays.enemy_ground += ground_inf
            arrays.enemy_air += air_inf
            arrays.enemy_anti_chaff += anti_chaff_inf
            arrays.enemy_anti_heavy += anti_heavy_inf
            arrays.enemy_durability += durability_inf
            if artillery_inf is not None:
                arrays.enemy_artillery += artillery_inf

    def _aggregate_zones(
        self,
        arrays: InfluenceMapArrays,
        frame: CoordinateFrame,
    ) -> list[ZoneInfluenceSummary]:
        norm_my_ground = _normalize(arrays.my_ground)
        norm_enemy_ground = _normalize(arrays.enemy_ground)
        norm_my_air = _normalize(arrays.my_air)
        norm_enemy_air = _normalize(arrays.enemy_air)
        norm_my_anti_chaff = _normalize(arrays.my_anti_chaff)
        norm_enemy_anti_chaff = _normalize(arrays.enemy_anti_chaff)
        norm_my_anti_heavy = _normalize(arrays.my_anti_heavy)
        norm_enemy_anti_heavy = _normalize(arrays.enemy_anti_heavy)

        all_dps = np.maximum(arrays.my_ground + arrays.enemy_ground, _EPSILON)
        norm_danger_ground = _normalize(
            arrays.enemy_ground / all_dps * arrays.enemy_ground
        )
        all_air = np.maximum(arrays.my_air + arrays.enemy_air, _EPSILON)
        norm_danger_air = _normalize(arrays.enemy_air / all_air * arrays.enemy_air)

        norm_opp = _normalize(np.maximum(arrays.my_ground - arrays.enemy_ground, 0))

        h, w = arrays.my_ground.shape
        col_edges = np.linspace(0, w, _ZONE_COLS + 1, dtype=int)

        is_negative_y = frame.side == PlayerSide.NEGATIVE_Y
        opp = frame.opponent_frame()
        all_y_lo = min(frame.front_y, frame.back_y, opp.front_y, opp.back_y)
        all_y_hi = max(frame.front_y, frame.back_y, opp.front_y, opp.back_y)
        y_span = all_y_hi - all_y_lo
        if y_span == 0:
            y_span = 1

        my_y_lo = min(frame.front_y, frame.back_y)
        my_y_hi = max(frame.front_y, frame.back_y)
        frac_lo = (my_y_lo - all_y_lo) / y_span
        frac_hi = (my_y_hi - all_y_lo) / y_span
        row_start = int(frac_lo * h)
        row_end = max(row_start + _ZONE_ROWS, int(frac_hi * h))
        row_start = max(0, row_start)
        row_end = min(h, row_end)

        row_edges = np.linspace(row_start, row_end, _ZONE_ROWS + 1, dtype=int)

        zones: list[ZoneInfluenceSummary] = []
        for ri in range(_ZONE_ROWS):
            r0, r1 = row_edges[ri], row_edges[ri + 1]
            if r1 <= r0:
                r1 = r0 + 1
            for ci in range(_ZONE_COLS):
                c0, c1 = col_edges[ci], col_edges[ci + 1]

                if is_negative_y:
                    zone_id = _ZONE_GRID[_ZONE_ROWS - 1 - ri][ci]
                else:
                    zone_id = _ZONE_GRID[ri][ci]

                zones.append(
                    ZoneInfluenceSummary.clamped(
                        zone=zone_id,
                        my_ground=float(norm_my_ground[r0:r1, c0:c1].mean()),
                        enemy_ground=float(norm_enemy_ground[r0:r1, c0:c1].mean()),
                        my_air=float(norm_my_air[r0:r1, c0:c1].mean()),
                        enemy_air=float(norm_enemy_air[r0:r1, c0:c1].mean()),
                        my_anti_chaff=float(norm_my_anti_chaff[r0:r1, c0:c1].mean()),
                        enemy_anti_chaff=float(
                            norm_enemy_anti_chaff[r0:r1, c0:c1].mean()
                        ),
                        my_anti_heavy=float(norm_my_anti_heavy[r0:r1, c0:c1].mean()),
                        enemy_anti_heavy=float(
                            norm_enemy_anti_heavy[r0:r1, c0:c1].mean()
                        ),
                        danger_for_my_ground=float(
                            norm_danger_ground[r0:r1, c0:c1].mean()
                        ),
                        danger_for_my_air=float(norm_danger_air[r0:r1, c0:c1].mean()),
                        opportunity_score=float(norm_opp[r0:r1, c0:c1].mean()),
                    )
                )

        return zones
