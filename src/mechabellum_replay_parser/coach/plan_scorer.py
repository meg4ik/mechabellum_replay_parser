from __future__ import annotations

from .feature_extractor import (
    ANTI_AIR_UNITS,
    ANTI_CHAFF_UNITS,
    ANTI_HEAVY_UNITS,
    FLANK_UNITS,
    SCALING_UNITS,
)
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
}

_MOVEMENT_RESPONSE_TYPES = frozenset(
    {"spread_units", "reduce_aoe_exposure", "rebuild_construction", "protect_flanks"}
)

_WEIGHTS: dict[str, float] = {
    "threat_coverage": 0.35,
    "tempo": 0.20,
    "supply_efficiency": 0.15,
    "positioning_safety": 0.15,
    "flexibility_next_round": 0.10,
    "tower_protection": 0.10,
    "scaling": 0.05,
    "overreaction_risk": -0.20,
    "legality_penalty": -1.00,
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


class PlanScorer:
    def score_all(
        self,
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        features: TacticalFeatures,
        state: StateView,
    ) -> list[PlanScoreBreakdown]:
        return [self.score(plan, v, features, state) for plan, v in validated_plans]

    def score(
        self,
        plan: CandidatePlan,
        validation: PlanValidationResult,
        features: TacticalFeatures,
        state: StateView,
    ) -> PlanScoreBreakdown:
        reasons: list[str] = []
        warnings: list[str] = []
        supply = state.my_supply or 0
        cost = plan.total_cost
        buys = _buy_units(plan.action_ids)

        # legality
        legality_penalty = 0.0 if validation.is_valid else 1.0
        if not validation.is_valid:
            codes = [i.code for i in validation.issues]
            warnings.append(f"Plan invalid: {codes}")

        # threat_coverage
        top_threats = sorted(features.threats, key=lambda t: t.severity, reverse=True)[:3]
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

        # supply_efficiency
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

        # tempo
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

        # scaling
        scaling = 0.8 if buys & SCALING_UNITS else 0.3

        # positioning_safety
        clump_threat = any(t.key == "positioning_clump_risk" for t in features.threats)
        if clump_threat:
            positioning_safety = 0.8 if _has_reposition(plan.action_ids) else 0.3
            if not _has_reposition(plan.action_ids):
                warnings.append("Clump risk detected but plan has no move/keep actions.")
        else:
            positioning_safety = 0.6

        # tower_protection
        tower_risk = any(
            t.key == "construction_lost" for t in features.threats
        ) or any("tower_exposure" in note for note in features.tower_notes)
        if tower_risk:
            tower_protection = 0.8 if _has_reposition(plan.action_ids) else 0.2
            if not _has_reposition(plan.action_ids):
                warnings.append("Tower at risk but plan has no reposition actions.")
        else:
            tower_protection = 0.5

        # flexibility_next_round
        remaining = supply - cost
        if remaining >= 200:
            flexibility_next_round = 1.0
        elif remaining >= 100:
            flexibility_next_round = 0.8
        elif remaining >= 0:
            flexibility_next_round = 0.5
        else:
            flexibility_next_round = 0.0

        # overreaction_risk
        overreaction_risk = 0.0
        if not features.threats and cost > supply * 0.8 and supply > 0:
            overreaction_risk = 0.4
            reasons.append("Heavy spend with no active threats.")

        # total_score (clamped 0..1)
        raw = (
            threat_coverage * _WEIGHTS["threat_coverage"]
            + tempo * _WEIGHTS["tempo"]
            + supply_efficiency * _WEIGHTS["supply_efficiency"]
            + positioning_safety * _WEIGHTS["positioning_safety"]
            + flexibility_next_round * _WEIGHTS["flexibility_next_round"]
            + tower_protection * _WEIGHTS["tower_protection"]
            + scaling * _WEIGHTS["scaling"]
            + overreaction_risk * _WEIGHTS["overreaction_risk"]
            + legality_penalty * _WEIGHTS["legality_penalty"]
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
            reasons=reasons,
            warnings=warnings,
        )
