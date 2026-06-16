from __future__ import annotations

from collections import Counter

from .schemas import (
    ArmyProfile,
    AnswerStrength,
    ConstructionStatus,
    StateView,
    TacticalFeatures,
    ThreatSignal,
    ThreatUrgency,
    UnitView,
)
from .unit_roles import get_tags

# ── Unit taxonomy (kept for fast set-ops without JSON lookup) ─────────────────

AIR_UNITS = frozenset(
    {"phoenix", "wasp", "overlord", "wraith", "phantom ray", "typhoon"}
)
ANTI_AIR_UNITS = frozenset({"arclight", "mustang", "marksmen", "stormcaller"})
CHAFF_UNITS = frozenset({"crawler", "fang", "hound"})
ANTI_CHAFF_UNITS = frozenset(
    {"arclight", "vulcan", "fire badger", "stormcaller", "mustang"}
)
ARTILLERY_UNITS = frozenset(
    {"stormcaller", "marksmen", "melting point", "sledgehammer", "farseer", "scorpion"}
)
HEAVY_FRONTLINE_UNITS = frozenset(
    {"fortress", "rhino", "steel ball", "sabertooth", "sandworm", "tarantula"}
)
ANTI_HEAVY_UNITS = frozenset(
    {"marksmen", "melting point", "phoenix", "scorpion", "raiden"}
)
SCALING_UNITS = frozenset(
    {"warfactory", "abyss", "overlord", "scorpion", "raiden", "wraith", "farseer"}
)
FLANK_UNITS = frozenset(
    {"crawler", "fang", "hound", "phoenix", "wasp", "typhoon", "phantom ray"}
)

_CHAFF_THRESHOLD = 4


# ── Helpers ───────────────────────────────────────────────────────────────────


def _urgency(severity: float) -> ThreatUrgency:
    if severity >= 0.8:
        return ThreatUrgency.CRITICAL
    if severity >= 0.6:
        return ThreatUrgency.HIGH
    if severity >= 0.4:
        return ThreatUrgency.MEDIUM
    return ThreatUrgency.LOW


def _army_profile(units: list[UnitView]) -> ArmyProfile:
    if not units:
        return ArmyProfile()
    tag_counts: Counter = Counter()
    for u in units:
        for tag in get_tags(u.name):
            tag_counts[tag] += 1
    total = len(units)

    def frac(tag: str) -> float:
        return min(tag_counts[tag] / total, 1.0)

    return ArmyProfile(
        chaff=frac("chaff"),
        anti_chaff=frac("anti_chaff"),
        anti_air=frac("anti_air"),
        air_pressure=frac("air"),
        single_target=frac("single_target"),
        heavy_frontline=frac("heavy_frontline"),
        artillery=frac("artillery"),
        backline_carry=frac("backline_carry"),
        flank_pressure=frac("flank_pressure"),
        tankiness=frac("tank"),
        scaling=frac("scaling"),
    )


class FeatureExtractor:
    def extract(self, state: StateView) -> TacticalFeatures:
        threats: list[ThreatSignal] = []
        my_weaknesses: list[str] = []
        enemy_weaknesses: list[str] = []
        tower_notes: list[str] = []
        likely_continuation: list[str] = []
        priority_questions: list[str] = []

        my_unit_names = {u.name for u in state.my_state.units}
        enemy_units = [u for es in state.enemy_states for u in es.units]
        enemy_unit_names = {u.name for u in enemy_units}

        my_profile = _army_profile(state.my_state.units)
        enemy_profile = _army_profile(enemy_units)

        # ── Air pressure ──────────────────────────────────────────────────────
        enemy_air = enemy_unit_names & AIR_UNITS
        if enemy_air:
            my_aa = my_unit_names & ANTI_AIR_UNITS
            if not my_aa:
                answer, severity = AnswerStrength.NONE, 0.9
                my_weaknesses.append("no anti-air")
            elif len(my_aa) == 1:
                answer, severity = AnswerStrength.WEAK, 0.6
                my_weaknesses.append("thin anti-air coverage")
            else:
                answer, severity = AnswerStrength.STRONG, 0.2
            threats.append(
                ThreatSignal(
                    key="enemy_air_pressure",
                    severity=severity,
                    urgency=_urgency(severity),
                    source_units=sorted(enemy_air),
                    explanation=(
                        f"Enemy has {', '.join(sorted(enemy_air))} — "
                        "air units that bypass ground defenses."
                    ),
                    my_answer=answer,
                    recommended_response_types=["add_anti_air", "upgrade_anti_air"],
                    bad_response_types=["more_ground_chaff", "slow_ground_only"],
                )
            )

        # ── Chaff overload ────────────────────────────────────────────────────
        enemy_chaff_count = sum(1 for u in enemy_units if u.name in CHAFF_UNITS)
        if enemy_chaff_count >= _CHAFF_THRESHOLD:
            my_ac = my_unit_names & ANTI_CHAFF_UNITS
            answer = AnswerStrength.STRONG if my_ac else AnswerStrength.NONE
            severity = 0.3 if my_ac else 0.7
            if not my_ac:
                my_weaknesses.append("no splash damage vs chaff")
            threats.append(
                ThreatSignal(
                    key="enemy_chaff_overload",
                    severity=severity,
                    urgency=_urgency(severity),
                    source_units=sorted(enemy_unit_names & CHAFF_UNITS),
                    explanation=(
                        f"Enemy has {enemy_chaff_count} chaff units — splash damage needed."
                    ),
                    my_answer=answer,
                    recommended_response_types=[
                        "add_splash",
                        "add_arclight",
                        "add_vulcan",
                    ],
                    bad_response_types=["more_single_target", "heavy_frontline_only"],
                )
            )

        # ── Artillery pressure ────────────────────────────────────────────────
        enemy_art = enemy_unit_names & ARTILLERY_UNITS
        if enemy_art:
            my_flank = my_unit_names & FLANK_UNITS
            answer = AnswerStrength.MEDIUM if my_flank else AnswerStrength.NONE
            severity = 0.3 if my_flank else 0.5
            threats.append(
                ThreatSignal(
                    key="enemy_artillery_pressure",
                    severity=severity,
                    urgency=_urgency(severity),
                    source_units=sorted(enemy_art),
                    explanation=(
                        f"Enemy has {', '.join(sorted(enemy_art))} — long-range backline threat."
                    ),
                    my_answer=answer,
                    recommended_response_types=["add_flank_pressure", "add_fast_units"],
                    bad_response_types=["slow_backline_scaling", "cluster_units"],
                )
            )

        # ── Heavy frontline wall ──────────────────────────────────────────────
        enemy_heavy = enemy_unit_names & HEAVY_FRONTLINE_UNITS
        enemy_heavy_count = sum(
            1 for u in enemy_units if u.name in HEAVY_FRONTLINE_UNITS
        )
        if enemy_heavy_count >= 2:
            my_ah = my_unit_names & ANTI_HEAVY_UNITS
            answer = AnswerStrength.STRONG if my_ah else AnswerStrength.NONE
            severity = 0.25 if my_ah else 0.5
            if not my_ah:
                my_weaknesses.append("no anti-heavy single-target damage")
            threats.append(
                ThreatSignal(
                    key="enemy_frontline_wall",
                    severity=severity,
                    urgency=_urgency(severity),
                    source_units=sorted(enemy_heavy),
                    explanation=(
                        "Enemy has a heavy frontline — sustained single-target damage needed."
                    ),
                    my_answer=answer,
                    recommended_response_types=[
                        "add_single_target",
                        "add_marksmen",
                        "add_melting_point",
                    ],
                    bad_response_types=["more_chaff_only", "spread_thin"],
                )
            )

        # ── Enemy scaling carry ───────────────────────────────────────────────
        enemy_scaling = enemy_unit_names & SCALING_UNITS
        if enemy_scaling and enemy_profile.scaling > 0.2:
            threats.append(
                ThreatSignal(
                    key="enemy_has_scaling_carry",
                    severity=0.6,
                    urgency=ThreatUrgency.HIGH,
                    source_units=sorted(enemy_scaling),
                    explanation=(
                        f"Enemy has scaling units ({', '.join(sorted(enemy_scaling))}) "
                        "— they get stronger each round."
                    ),
                    my_answer=AnswerStrength.UNKNOWN,
                    recommended_response_types=[
                        "close_game_quickly",
                        "add_flank_pressure",
                    ],
                    bad_response_types=["slow_scaling_race", "passive_play"],
                )
            )

        # ── Enemy weaknesses ──────────────────────────────────────────────────
        if not (enemy_unit_names & ANTI_AIR_UNITS) and (my_unit_names & AIR_UNITS):
            enemy_weaknesses.append("no anti-air — our air units should dominate")
        if not (enemy_unit_names & ANTI_CHAFF_UNITS):
            my_chaff_count = sum(
                1 for u in state.my_state.units if u.name in CHAFF_UNITS
            )
            if my_chaff_count >= 3:
                enemy_weaknesses.append(
                    "no splash vs our chaff — chaff flood is strong"
                )
        if not (enemy_unit_names & ANTI_HEAVY_UNITS) and (
            my_unit_names & HEAVY_FRONTLINE_UNITS
        ):
            enemy_weaknesses.append("no anti-heavy — our frontline should dominate")

        # ── Positioning clump risk ────────────────────────────────────────────
        unit_positions = [u.position for u in state.my_state.units if u.position]
        if len(unit_positions) >= 3:
            xs = [p.x for p in unit_positions]
            ys = [p.y for p in unit_positions]
            if (max(xs) - min(xs)) < 100 and (max(ys) - min(ys)) < 80:
                threats.append(
                    ThreatSignal(
                        key="positioning_clump_risk",
                        severity=0.45,
                        urgency=ThreatUrgency.MEDIUM,
                        source_units=[],
                        explanation="My units are tightly clustered — vulnerable to AoE.",
                        my_answer=AnswerStrength.NONE,
                        recommended_response_types=[
                            "spread_units",
                            "reduce_aoe_exposure",
                        ],
                        bad_response_types=["cluster_backline"],
                    )
                )

        # ── Construction signals ──────────────────────────────────────────────
        if not state.my_state.constructions:
            tower_notes.append("No constructions visible for this player.")
        else:
            for c in state.my_state.constructions:
                pos_str = c.position_label or (
                    f"({c.position.x}, {c.position.y})" if c.position else "unknown pos"
                )
                tower_notes.append(
                    f"{c.type.value} ({c.role.value}) at {pos_str} — {c.status.value}."
                )
            for c in state.my_state.constructions:
                if c.position and c.status == ConstructionStatus.ALIVE:
                    if c.position.x < -100:
                        tower_notes.append(
                            f"tower_exposure_left: {c.type.value} at x={c.position.x} may be flanked."
                        )
                    elif c.position.x > 100:
                        tower_notes.append(
                            f"tower_exposure_right: {c.type.value} at x={c.position.x} may be flanked."
                        )

        # Lost constructions from strategic memory
        lost_events = [
            e for e in state.strategic_memory.critical_events if "disappeared" in e
        ]
        if lost_events:
            threats.append(
                ThreatSignal(
                    key="construction_lost",
                    severity=0.6,
                    urgency=ThreatUrgency.HIGH,
                    source_units=[],
                    explanation=(
                        f"{len(lost_events)} construction(s) lost: "
                        + "; ".join(lost_events[:2])
                    ),
                    my_answer=AnswerStrength.NONE,
                    recommended_response_types=[
                        "rebuild_construction",
                        "protect_flanks",
                    ],
                    bad_response_types=["ignore_construction_loss"],
                )
            )
            for e in lost_events:
                tower_notes.append(f"[LOST] {e}")

        # Construction advantage / disadvantage
        my_live = sum(
            1
            for c in state.my_state.constructions
            if c.status == ConstructionStatus.ALIVE
        )
        enemy_live = sum(
            1
            for es in state.enemy_states
            for c in es.constructions
            if c.status == ConstructionStatus.ALIVE
        )
        if enemy_live > my_live:
            tower_notes.append(
                f"Construction disadvantage: enemy has {enemy_live}, we have {my_live}."
            )

        # ── Tempo ─────────────────────────────────────────────────────────────
        my_av = state.my_state.army_value or 0
        enemy_av_total = sum(es.army_value or 0 for es in state.enemy_states)
        if enemy_av_total == 0 and my_av == 0:
            tempo_state = "unknown"
        elif enemy_av_total == 0:
            tempo_state = "ahead"
        elif my_av > enemy_av_total * 1.15:
            tempo_state = "ahead"
        elif my_av < enemy_av_total * 0.85:
            tempo_state = "behind"
        else:
            tempo_state = "even"

        # ── Board posture ─────────────────────────────────────────────────────
        ys = [u.position.y for u in state.my_state.units if u.position]
        if not ys:
            board_posture = "unknown"
        else:
            avg_y = sum(ys) / len(ys)
            if avg_y > -120:
                board_posture = "aggro"
            elif avg_y > -200:
                board_posture = "standard"
            else:
                board_posture = "defensive"

        # ── Likely enemy continuation from strategic memory ────────────────
        likely_continuation.extend(state.strategic_memory.do_not_forget)

        # ── Priority questions ────────────────────────────────────────────────
        if tempo_state == "behind":
            priority_questions.append("How to recover army value this round?")
        if tempo_state == "ahead":
            priority_questions.append(
                "How to press the advantage without overextending?"
            )
        high_sev = [t for t in threats if t.severity >= 0.7]
        if high_sev:
            priority_questions.append(f"Urgent: address {high_sev[0].key} first.")

        return TacticalFeatures(
            threats=threats,
            my_weaknesses=my_weaknesses,
            enemy_weaknesses=enemy_weaknesses,
            tempo_state=tempo_state,
            board_posture=board_posture,
            tower_notes=tower_notes,
            likely_enemy_continuation=likely_continuation,
            priority_questions=priority_questions,
            my_army_profile=my_profile,
            enemy_army_profile=enemy_profile,
        )
