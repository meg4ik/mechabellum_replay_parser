from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .schemas import UnitView

_DATA_DIR = Path(__file__).parent.parent / "data"


@lru_cache(maxsize=1)
def _load_combat_data() -> dict:
    with (_DATA_DIR / "unit_combat_data.json").open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_tech_modifiers() -> dict:
    with (_DATA_DIR / "tech_modifiers.json").open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_matchup_modifiers() -> dict:
    with (_DATA_DIR / "unit_matchup_modifiers.json").open(encoding="utf-8") as f:
        return json.load(f)


class UnitTargetProfile(BaseModel):
    can_hit_ground: bool = True
    can_hit_air: bool = False
    prefers_chaff: bool = False
    prefers_heavy: bool = False
    splash: bool = False


class UnitCombatStats(BaseModel):
    unit: str
    base_hp: float
    base_dps_ground: float = 0.0
    base_dps_air: float = 0.0
    range: float
    speed: float | None = None
    squad_size: int = 1
    tags: set[str] = Field(default_factory=set)
    target_profile: UnitTargetProfile


class ResolvedUnitStats(BaseModel):
    unit: str
    level: int
    effective_hp: float
    effective_dps_ground: float
    effective_dps_air: float
    effective_range: float
    anti_chaff_score: float
    anti_heavy_score: float
    tags: set[str]
    applied_modifiers: list[str]


_FALLBACK = UnitCombatStats(
    unit="unknown",
    base_hp=100,
    base_dps_ground=10,
    base_dps_air=0,
    range=50,
    speed=5,
    squad_size=1,
    tags=set(),
    target_profile=UnitTargetProfile(),
)


def _parse_combat_entry(name: str, raw: dict) -> UnitCombatStats:
    return UnitCombatStats(
        unit=name,
        base_hp=raw["base_hp"],
        base_dps_ground=raw.get("base_dps_ground", 0.0),
        base_dps_air=raw.get("base_dps_air", 0.0),
        range=raw["range"],
        speed=raw.get("speed"),
        squad_size=raw.get("squad_size", 1),
        tags=set(raw.get("tags", [])),
        target_profile=UnitTargetProfile(
            can_hit_ground=raw.get("can_hit_ground", True),
            can_hit_air=raw.get("can_hit_air", False),
            prefers_chaff=raw.get("prefers_chaff", False),
            prefers_heavy=raw.get("prefers_heavy", False),
            splash=raw.get("splash", False),
        ),
    )


def get_combat_stats(name: str) -> UnitCombatStats:
    data = _load_combat_data()
    raw = data.get(name.lower())
    if raw is None:
        return _FALLBACK.model_copy(update={"unit": name.lower()})
    return _parse_combat_entry(name.lower(), raw)


class UnitStatsResolver:
    def resolve_unit(
        self,
        unit_view: UnitView,
        active_techs: list[dict] | None = None,
    ) -> ResolvedUnitStats:
        base = get_combat_stats(unit_view.name)
        level = unit_view.level or 1
        level_mult = 1.0 + 0.35 * (level - 1)

        hp = base.base_hp * level_mult
        dps_g = base.base_dps_ground * level_mult
        dps_a = base.base_dps_air * level_mult
        rng = float(base.range)

        applied: list[str] = []
        tech_mods = _load_tech_modifiers()

        tech_names = unit_view.active_techs or []
        if active_techs:
            for t in active_techs:
                if isinstance(t, dict):
                    tname = t.get("tech", "")
                    tunit = t.get("unit", "")
                    if (
                        tunit.lower() == unit_view.name.lower()
                        and tname not in tech_names
                    ):
                        tech_names.append(tname)

        for tname in tech_names:
            mod = tech_mods.get(tname)
            if mod is None:
                continue
            applied.append(tname)
            hp *= mod.get("hp_multiplier", 1.0)
            dps_g *= mod.get("dps_ground_multiplier", 1.0)
            dps_a *= mod.get("dps_air_multiplier", 1.0)
            rng *= mod.get("range_multiplier", 1.0)

        matchups = _load_matchup_modifiers()
        unit_matchup = matchups.get(unit_view.name.lower(), {})
        anti_chaff = unit_matchup.get("ground_chaff", 0.5)
        anti_heavy = unit_matchup.get("ground_heavy", 0.5)

        return ResolvedUnitStats(
            unit=unit_view.name.lower(),
            level=level,
            effective_hp=round(hp, 1),
            effective_dps_ground=round(dps_g, 1),
            effective_dps_air=round(dps_a, 1),
            effective_range=round(rng, 1),
            anti_chaff_score=anti_chaff,
            anti_heavy_score=anti_heavy,
            tags=base.tags,
            applied_modifiers=applied,
        )

    def resolve_many(
        self,
        units: list[UnitView],
        active_techs: list[dict] | None = None,
    ) -> dict[str, ResolvedUnitStats]:
        result: dict[str, ResolvedUnitStats] = {}
        for u in units:
            key = f"{u.name.lower()}_{u.index or 0}"
            result[key] = self.resolve_unit(u, active_techs)
        return result
