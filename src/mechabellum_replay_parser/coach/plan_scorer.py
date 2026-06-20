from __future__ import annotations

from .feature_extractor import (
    ANTI_AIR_UNITS,
    ANTI_CHAFF_UNITS,
    ANTI_HEAVY_UNITS,
    FLANK_UNITS,
    SCALING_UNITS,
)
from .influence_schemas import InfluenceAnalysisSummary, TacticalInfluenceFinding
from .schemas import (
    CandidatePlan,
    PlanScoreBreakdown,
    PlanValidationResult,
    StateView,
    TacticalFeatures,
    ThreatSignal,
)

_RESPONSE_TYPE_TO_UNITS: dict[str, frozenset[str]] = {
    "add_anti_air": ANTI_AIR_UNITS,
    "upgrade_anti_air": ANTI_AIR_UNITS,
    "add_splash": ANTI_CHAFF_UNITS,
    "add_arclight": frozenset({"arclight"}),
    "add_vulcan": frozenset({"vulcan"}),
    "add_flank_pressure": FLANK_UNITS,
    "add_fast_units": FLANK_UNITS,
    "close_game_quickly": FLANK_UNITS,
    "add_single_target": ANTI_HEAVY_UNITS,
    "add_marksmen": frozenset({"marksmen"}),
    "add_melting_point": frozenset({"melting point"}),
    "add_anti_chaff": ANTI_CHAFF_UNITS,
    "upgrade_splash": ANTI_CHAFF_UNITS,
    "spread_chaff_clear": ANTI_CHAFF_UNITS,
    "unlock_anti_heavy": ANTI_HEAVY_UNITS,
    "damage_scaling": ANTI_HEAVY_UNITS | SCALING_UNITS,
    "shift_anti_air": ANTI_AIR_UNITS,
    "anti_air_tech": ANTI_AIR_UNITS,
}

_MOVEMENT_RESPONSE_TYPES = frozenset(
    {
        "spread_units",
        "reduce_aoe_exposure",
        "rebuild_construction",
        "protect_flanks",
        "spread_backline",
        "pressure_artillery",
        "flank_attack",
        "shield_or_protection",
        "flank_pressure",
        "fast_chaff_flank",
        "protect_tower",
        "move_chaff_to_cover",
        "add_frontline",
    }
)

_FINDING_KEY_TO_RESPONSE_CATEGORY: dict[str, str] = {
    "anti_air_gap": "anti_air",
    "anti_chaff_gap": "anti_chaff",
    "anti_heavy_gap": "anti_heavy",
    "artillery_danger": "artillery",
}

_BASE_WEIGHTS: dict[str, float] = {
    "threat_coverage": 0.25,
    "tempo": 0.15,
    "supply_efficiency": 0.10,
    "positioning_safety": 0.15,
    "flexibility_next_round": 0.05,
    "tower_protection": 0.05,
    "scaling": 0.05,
    "overreaction_risk": -0.10,
    "legality_penalty": -1.00,
    "influence_improvement": 0.25,
}

_NO_INFLUENCE_WEIGHTS: dict[str, float] = {
    "threat_coverage": 0.35,
    "tempo": 0.20,
    "supply_efficiency": 0.15,
    "positioning_safety": 0.15,
    "flexibility_next_round": 0.10,
    "tower_protection": 0.10,
    "scaling": 0.05,
    "overreaction_risk": -0.20,
    "legality_penalty": -1.00,
    "influence_improvement": 0.0,
}


def _buy_units(action_ids: list[str]) -> set[str]:
    return {aid[4:] for aid in action_ids if aid.startswith("buy_")}


def _has_reposition(action_ids: list[str]) -> bool:
    return any(aid.startswith("keep_") or aid.startswith("move_") for aid in action_ids)


def _covers_threat(buys: set[str], action_ids: list[str], threat: ThreatSignal) -> bool:
    has_repos = _has_reposition(action_ids)
    for rt in threat.recommended_response_types:
        if rt in _MOVEMENT_RESPONSE_TYPES:
            if has_repos:
                return True
        else:
            units = _RESPONSE_TYPE_TO_UNITS.get(rt, frozenset())
            if buys & units:
                return True
    return False


def _plan_addresses_finding(
    buys: set[str],
    action_ids: list[str],
    finding: TacticalInfluenceFinding,
) -> bool:
    has_repos = _has_reposition(action_ids)
    for rt in finding.recommended_response_types:
        if rt in _MOVEMENT_RESPONSE_TYPES:
            if has_repos:
                return True
        else:
            units = _RESPONSE_TYPE_TO_UNITS.get(rt, frozenset())
            if buys & units:
                return True
    return False


class PlanScorer:
    def score_all(
        self,
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        features: TacticalFeatures,
        state: StateView,
        influence: InfluenceAnalysisSummary | None = None,
    ) -> list[PlanScoreBreakdown]:
        return [
            self.score(plan, v, features, state, influence)
            for plan, v in validated_plans
        ]

    def score(
        self,
        plan: CandidatePlan,
        validation: PlanValidationResult,
        features: TacticalFeatures,
        state: StateView,
        influence: InfluenceAnalysisSummary | None = None,
    ) -> PlanScoreBreakdown:
        reasons: list[str] = []
        warnings: list[str] = []
        influence_explanation: list[str] = []
        supply = state.my_supply or 0
        cost = plan.total_cost
        buys = _buy_units(plan.action_ids)

        weights = _BASE_WEIGHTS if influence else _NO_INFLUENCE_WEIGHTS

        legality_penalty = 0.0 if validation.is_valid else 1.0
        if not validation.is_valid:
            codes = [i.code for i in validation.issues]
            warnings.append(f"Plan invalid: {codes}")

        top_threats = sorted(features.threats, key=lambda t: t.severity, reverse=True)[
            :3
        ]
        if top_threats:
            covered = sum(
                1 for t in top_threats if _covers_threat(buys, plan.action_ids, t)
            )
            threat_coverage = covered / len(top_threats)
            if covered == 0:
                warnings.append("Plan does not address any of the top threats.")
            else:
                reasons.append(f"Covers {covered}/{len(top_threats)} top threats.")
        else:
            threat_coverage = 0.7
            reasons.append("No active threats — free to invest.")

        if supply == 0:
            supply_efficiency = 0.5
        elif cost > supply:
            supply_efficiency = 0.0
            warnings.append(f"Overspend: {cost} > supply {supply}.")
        else:
            ratio = cost / supply
            if ratio >= 0.7:
                supply_efficiency = 1.0
            elif ratio >= 0.4:
                supply_efficiency = 0.7
            elif ratio > 0:
                supply_efficiency = 0.4
            else:
                supply_efficiency = 0.2
            reasons.append(f"Supply usage {ratio:.0%} ({cost}/{supply}).")

        has_buys = bool(buys)
        if features.tempo_state == "behind":
            tempo = 0.9 if has_buys else 0.3
            if not has_buys:
                warnings.append("Tempo behind but plan buys nothing.")
        elif features.tempo_state == "ahead":
            tempo = 0.6
        elif features.tempo_state == "even":
            tempo = 0.5
        else:
            tempo = 0.4

        scaling = 0.8 if buys & SCALING_UNITS else 0.3

        clump_threat = any(t.key == "positioning_clump_risk" for t in features.threats)
        if clump_threat:
            positioning_safety = 0.8 if _has_reposition(plan.action_ids) else 0.3
            if not _has_reposition(plan.action_ids):
                warnings.append(
                    "Clump risk detected but plan has no move/keep actions."
                )
        else:
            positioning_safety = 0.6

        tower_risk = any(t.key == "construction_lost" for t in features.threats) or any(
            "tower_exposure" in note for note in features.tower_notes
        )
        if tower_risk:
            tower_protection = 0.8 if _has_reposition(plan.action_ids) else 0.2
            if not _has_reposition(plan.action_ids):
                warnings.append("Tower at risk but plan has no reposition actions.")
        else:
            tower_protection = 0.5

        remaining = supply - cost
        if remaining >= 200:
            flexibility_next_round = 1.0
        elif remaining >= 100:
            flexibility_next_round = 0.8
        elif remaining >= 0:
            flexibility_next_round = 0.5
        else:
            flexibility_next_round = 0.0

        overreaction_risk = 0.0
        if not features.threats and cost > supply * 0.8 and supply > 0:
            overreaction_risk = 0.4
            reasons.append("Heavy spend with no active threats.")

        inf_improvement, anti_air_imp, anti_chaff_imp, anti_heavy_imp, art_risk_red = (
            self._compute_influence_scores(
                buys,
                plan.action_ids,
                influence,
                influence_explanation,
            )
        )

        if influence and inf_improvement < 0.2 and features.threats:
            has_forbidden = any(
                rt in (buys | set(plan.action_ids))
                for f in (influence.tactical_findings or [])
                for rt in f.forbidden_response_types
            )
            if has_forbidden:
                overreaction_risk = max(overreaction_risk, 0.3)
                influence_explanation.append("Plan uses a forbidden response type.")

        raw = (
            threat_coverage * weights["threat_coverage"]
            + tempo * weights["tempo"]
            + supply_efficiency * weights["supply_efficiency"]
            + positioning_safety * weights["positioning_safety"]
            + flexibility_next_round * weights["flexibility_next_round"]
            + tower_protection * weights["tower_protection"]
            + scaling * weights["scaling"]
            + overreaction_risk * weights["overreaction_risk"]
            + legality_penalty * weights["legality_penalty"]
            + inf_improvement * weights["influence_improvement"]
        )
        total_score = max(0.0, min(1.0, raw))

        return PlanScoreBreakdown(
            plan_id=plan.id,
            total_score=round(total_score, 4),
            threat_coverage=round(threat_coverage, 4),
            supply_efficiency=round(supply_efficiency, 4),
            tempo=round(tempo, 4),
            scaling=round(scaling, 4),
            positioning_safety=round(positioning_safety, 4),
            tower_protection=round(tower_protection, 4),
            flexibility_next_round=round(flexibility_next_round, 4),
            overreaction_risk=round(overreaction_risk, 4),
            legality_penalty=round(legality_penalty, 4),
            influence_improvement=round(inf_improvement, 4),
            anti_air_improvement=round(anti_air_imp, 4),
            anti_chaff_improvement=round(anti_chaff_imp, 4),
            anti_heavy_improvement=round(anti_heavy_imp, 4),
            artillery_risk_reduction=round(art_risk_red, 4),
            influence_explanation=influence_explanation,
            reasons=reasons,
            warnings=warnings,
        )

    def _compute_influence_scores(
        self,
        buys: set[str],
        action_ids: list[str],
        influence: InfluenceAnalysisSummary | None,
        explanations: list[str],
    ) -> tuple[float, float, float, float, float]:
        if not influence:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if not influence.tactical_findings:
            return 0.5, 0.0, 0.0, 0.0, 0.0

        findings = influence.tactical_findings
        anti_air_imp = 0.0
        anti_chaff_imp = 0.0
        anti_heavy_imp = 0.0
        art_risk_red = 0.0

        addressed_severity = 0.0
        total_severity = 0.0

        for f in findings:
            total_severity += f.severity
            addressed = _plan_addresses_finding(buys, action_ids, f)
            if addressed:
                addressed_severity += f.severity
                if f.key == "anti_air_gap":
                    anti_air_imp = max(anti_air_imp, f.severity)
                    explanations.append(
                        f"Addresses anti-air gap (severity {f.severity:.2f}) in {f.zone.value if f.zone else 'global'}."
                    )
                elif f.key == "anti_chaff_gap":
                    anti_chaff_imp = max(anti_chaff_imp, f.severity)
                    explanations.append(
                        f"Addresses anti-chaff gap (severity {f.severity:.2f}) in {f.zone.value if f.zone else 'global'}."
                    )
                elif f.key == "anti_heavy_gap":
                    anti_heavy_imp = max(anti_heavy_imp, f.severity)
                    explanations.append(
                        f"Addresses anti-heavy gap (severity {f.severity:.2f}) in {f.zone.value if f.zone else 'global'}."
                    )
                elif f.key == "artillery_danger":
                    art_risk_red = max(art_risk_red, f.severity)
                    explanations.append(
                        f"Reduces artillery danger (severity {f.severity:.2f}) in {f.zone.value if f.zone else 'global'}."
                    )

        if total_severity > 0:
            influence_improvement = addressed_severity / total_severity
        else:
            influence_improvement = 0.5

        return (
            max(0.0, min(1.0, influence_improvement)),
            max(0.0, min(1.0, anti_air_imp)),
            max(0.0, min(1.0, anti_chaff_imp)),
            max(0.0, min(1.0, anti_heavy_imp)),
            max(0.0, min(1.0, art_risk_red)),
        )
