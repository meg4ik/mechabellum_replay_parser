from __future__ import annotations

from .influence_map import InfluenceMapResult
from .influence_schemas import (
    InfluenceAnalysisSummary,
    MapZone,
    TacticalInfluenceFinding,
    ZoneInfluenceSummary,
)
from .schemas import StateView, TacticalFeatures

_SEVERITY_IMPORTANCE = {
    "air": 1.0,
    "artillery": 0.9,
    "heavy": 0.8,
    "tower": 0.8,
    "chaff": 0.7,
    "flank": 0.6,
}

_MIN_SEVERITY = 0.15

_FRONT_ZONES = frozenset(
    {MapZone.LEFT_FRONT, MapZone.CENTER_FRONT, MapZone.RIGHT_FRONT}
)
_MID_ZONES = frozenset({MapZone.LEFT_MID, MapZone.CENTER_MID, MapZone.RIGHT_MID})
_BACK_ZONES = frozenset({MapZone.LEFT_BACK, MapZone.CENTER_BACK, MapZone.RIGHT_BACK})
_LEFT_ZONES = frozenset({MapZone.LEFT_FRONT, MapZone.LEFT_MID, MapZone.LEFT_BACK})
_RIGHT_ZONES = frozenset({MapZone.RIGHT_FRONT, MapZone.RIGHT_MID, MapZone.RIGHT_BACK})


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _zone_label(zone: MapZone) -> str:
    return zone.value.replace("_", " ")


class InfluenceAnalyzer:
    def analyze(
        self,
        state: StateView,
        features: TacticalFeatures,
        influence: InfluenceMapResult,
    ) -> InfluenceAnalysisSummary:
        zones = influence.zones

        findings: list[TacticalInfluenceFinding] = []

        findings.extend(self._check_anti_air_gap(zones, features))
        findings.extend(self._check_anti_chaff_gap(zones, features))
        findings.extend(self._check_anti_heavy_gap(zones, features))
        findings.extend(self._check_artillery_danger(zones, features))
        findings.extend(self._check_flank_opportunity(zones, features))
        findings.extend(self._check_tower_pressure(zones, state))

        findings.sort(key=lambda f: f.severity, reverse=True)

        critical = [
            z
            for z in zones
            if z.danger_for_my_ground > 0.5 or z.danger_for_my_air > 0.5
        ]

        global_assessment = self._build_global_assessment(zones, features)

        return InfluenceAnalysisSummary(
            grid=influence.grid,
            global_assessment=global_assessment,
            zones=zones,
            critical_zones=critical,
            tactical_findings=findings,
        )

    def _check_anti_air_gap(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        has_enemy_air_units = any(
            t.key == "enemy_air_pressure" for t in features.threats
        )

        if not has_enemy_air_units:
            return findings

        for z in zones:
            if z.my_air >= 0.3:
                continue
            gap = 1.0 - z.my_air
            severity = _clamp01(gap * _SEVERITY_IMPORTANCE["air"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="anti_air_gap",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy has air units but my anti-air coverage is only {z.my_air:.2f} in {_zone_label(z.zone)}.",
                    recommended_response_types=[
                        "add_anti_air",
                        "shift_anti_air",
                        "anti_air_tech",
                    ],
                )
            )
        return findings

    def _check_anti_chaff_gap(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        has_enemy_chaff = any(t.key == "enemy_chaff_overload" for t in features.threats)

        if not has_enemy_chaff:
            return findings

        for z in zones:
            if z.my_anti_chaff >= 0.3:
                continue
            gap = 1.0 - z.my_anti_chaff
            severity = _clamp01(gap * _SEVERITY_IMPORTANCE["chaff"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="anti_chaff_gap",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy has chaff flood but my anti-chaff coverage is only {z.my_anti_chaff:.2f} in {_zone_label(z.zone)}.",
                    recommended_response_types=[
                        "add_anti_chaff",
                        "upgrade_splash",
                        "spread_chaff_clear",
                    ],
                )
            )
        return findings

    def _check_anti_heavy_gap(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        has_enemy_heavy = any(t.key == "enemy_frontline_wall" for t in features.threats)

        if not has_enemy_heavy:
            return findings

        for z in zones:
            if z.my_anti_heavy >= 0.3:
                continue
            gap = 1.0 - z.my_anti_heavy
            severity = _clamp01(gap * _SEVERITY_IMPORTANCE["heavy"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="anti_heavy_gap",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy has heavy units but my anti-heavy coverage is only {z.my_anti_heavy:.2f} in {_zone_label(z.zone)}.",
                    recommended_response_types=[
                        "add_single_target",
                        "unlock_anti_heavy",
                        "damage_scaling",
                    ],
                )
            )
        return findings

    def _check_artillery_danger(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        back_and_mid = _BACK_ZONES | _MID_ZONES

        for z in zones:
            if z.zone not in back_and_mid:
                continue
            danger = max(z.enemy_ground, z.danger_for_my_ground)
            if danger < 0.1:
                continue
            severity = _clamp01(danger * _SEVERITY_IMPORTANCE["artillery"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="artillery_danger",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy pressure overlaps my backline/mid in {_zone_label(z.zone)} (danger {danger:.2f}).",
                    recommended_response_types=[
                        "spread_backline",
                        "pressure_artillery",
                        "flank_attack",
                        "shield_or_protection",
                    ],
                )
            )
        return findings

    def _check_flank_opportunity(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        flank_zones = _LEFT_ZONES | _RIGHT_ZONES

        for z in zones:
            if z.zone not in flank_zones:
                continue
            if z.enemy_ground > 0.25:
                continue
            if z.opportunity_score < 0.2:
                continue
            severity = _clamp01(z.opportunity_score * _SEVERITY_IMPORTANCE["flank"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="flank_opportunity",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy pressure low ({z.enemy_ground:.2f}) on {_zone_label(z.zone)} — opportunity score {z.opportunity_score:.2f}.",
                    recommended_response_types=["flank_pressure", "fast_chaff_flank"],
                )
            )
        return findings

    def _check_tower_pressure(
        self,
        zones: list[ZoneInfluenceSummary],
        state: StateView,
    ) -> list[TacticalInfluenceFinding]:
        findings: list[TacticalInfluenceFinding] = []
        if not state.my_state.constructions:
            return findings

        tower_zones: set[MapZone] = set()
        for c in state.my_state.constructions:
            if c.position_label:
                for mz in MapZone:
                    if mz.value in c.position_label:
                        tower_zones.add(mz)
                        break

        if not tower_zones:
            return findings

        for z in zones:
            if z.zone not in tower_zones:
                continue
            danger = max(z.danger_for_my_ground, z.enemy_ground)
            if danger < 0.1:
                continue
            severity = _clamp01(danger * _SEVERITY_IMPORTANCE["tower"])
            if severity < _MIN_SEVERITY:
                continue
            findings.append(
                TacticalInfluenceFinding(
                    key="tower_pressure",
                    severity=round(severity, 2),
                    zone=z.zone,
                    evidence=f"Enemy pressure {danger:.2f} overlaps my construction zone in {_zone_label(z.zone)}.",
                    recommended_response_types=[
                        "protect_tower",
                        "move_chaff_to_cover",
                        "add_frontline",
                    ],
                )
            )
        return findings

    def _build_global_assessment(
        self,
        zones: list[ZoneInfluenceSummary],
        features: TacticalFeatures,
    ) -> dict[str, str]:
        if not zones:
            return {}

        avg_my_ground = sum(z.my_ground for z in zones) / len(zones)
        avg_enemy_ground = sum(z.enemy_ground for z in zones) / len(zones)
        avg_my_air = sum(z.my_air for z in zones) / len(zones)
        avg_enemy_air = sum(z.enemy_air for z in zones) / len(zones)
        avg_danger = sum(z.danger_for_my_ground for z in zones) / len(zones)

        front = [z for z in zones if z.zone in _FRONT_ZONES]
        avg_my_front = sum(z.my_ground for z in front) / max(len(front), 1)
        avg_enemy_front = sum(z.enemy_ground for z in front) / max(len(front), 1)

        def _balance(my: float, enemy: float) -> str:
            diff = my - enemy
            if diff > 0.2:
                return "my_strongly_favored"
            if diff > 0.05:
                return "my_favored"
            if diff > -0.05:
                return "neutral"
            if diff > -0.2:
                return "enemy_favored"
            return "enemy_strongly_favored"

        assessment: dict[str, str] = {
            "ground_balance": _balance(avg_my_ground, avg_enemy_ground),
            "air_balance": _balance(avg_my_air, avg_enemy_air),
            "frontline_balance": _balance(avg_my_front, avg_enemy_front),
        }

        if avg_danger > 0.4:
            assessment["artillery_pressure"] = "high"
        elif avg_danger > 0.2:
            assessment["artillery_pressure"] = "moderate"
        else:
            assessment["artillery_pressure"] = "low"

        return assessment
