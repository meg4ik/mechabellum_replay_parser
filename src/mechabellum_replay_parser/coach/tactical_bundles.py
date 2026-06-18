from __future__ import annotations

from .feature_extractor import (
    ANTI_AIR_UNITS,
    ANTI_CHAFF_UNITS,
    FLANK_UNITS,
    SCALING_UNITS,
)
from .schemas import (
    AnswerStrength,
    Depth,
    Lane,
    LegalAction,
    PlacementAction,
    PlacementAnchor,
    PlacementIntent,
    StateView,
    TacticalBundle,
    TacticalFeatures,
    TacticalTheme,
    Zone,
)

_SINGLE_TARGET_UNITS = frozenset(
    {"marksmen", "melting point", "scorpion", "raiden", "phoenix"}
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _buy_map(legal_actions: list[LegalAction]) -> dict[str, str]:
    """unit_name → buy action ID for all available buys."""
    return {a.unit: a.id for a in legal_actions if a.type == "buy_unit" and a.unit}


def _unlock_map(legal_actions: list[LegalAction]) -> dict[str, str]:
    return {a.unit: a.id for a in legal_actions if a.type == "unlock_unit" and a.unit}


def _ids_for(unit_set: frozenset, action_map: dict[str, str]) -> list[str]:
    return [action_map[u] for u in unit_set if u in action_map]


def _min_cost(action_ids: list[str], legal_actions: list[LegalAction]) -> int:
    cost_map = {a.id: a.cost for a in legal_actions}
    costs = [
        cost_map[aid] for aid in action_ids if aid in cost_map and cost_map[aid] > 0
    ]
    return min(costs, default=0)


def _unit_from_id(action_id: str) -> str:
    if action_id.startswith("buy_"):
        return action_id[4:]
    if action_id.startswith("unlock_"):
        return action_id[7:]
    return "unit"


def _intent(
    action_id: str,
    lane: Lane,
    depth: Depth,
    anchor: PlacementAnchor = PlacementAnchor.NONE,
    purpose: str = "",
    zone: Zone = Zone.OWN,
) -> PlacementIntent:
    return PlacementIntent(
        unit=_unit_from_id(action_id),
        action=PlacementAction.NEW,
        lane=lane,
        depth=depth,
        zone=zone,
        anchor=anchor,
        purpose=purpose or None,
    )


# ── Generator ─────────────────────────────────────────────────────────────────


class TacticalBundleGenerator:
    def generate(
        self,
        state: StateView,
        features: TacticalFeatures,
        legal_actions: list[LegalAction],
    ) -> list[TacticalBundle]:
        bundles: list[TacticalBundle] = []
        threat_map = {t.key: t for t in features.threats}
        buys = _buy_map(legal_actions)
        unlocks = _unlock_map(legal_actions)
        move_ids = [a.id for a in legal_actions if a.type == "move_unit"]
        keep_ids = [a.id for a in legal_actions if a.type == "keep_unit"]
        flank_zone = Zone.OPPONENT if state.round >= 2 else Zone.OWN

        # ── ANTI_AIR_RESPONSE ─────────────────────────────────────────────────
        if "enemy_air_pressure" in threat_map:
            t = threat_map["enemy_air_pressure"]
            if t.my_answer != AnswerStrength.STRONG:
                aa_buy = _ids_for(ANTI_AIR_UNITS, buys)
                aa_unlock = _ids_for(ANTI_AIR_UNITS, unlocks)
                required = aa_unlock + aa_buy
                if required:
                    first = required[0]
                    bundles.append(
                        TacticalBundle(
                            id="bundle_anti_air",
                            theme=TacticalTheme.ANTI_AIR_RESPONSE,
                            title="Anti-air response",
                            target_threats=["enemy_air_pressure"],
                            required_action_ids=required,
                            estimated_cost=_min_cost(aa_buy, legal_actions),
                            placement_intents=[
                                _intent(
                                    first,
                                    Lane.CENTER,
                                    Depth.BACK,
                                    PlacementAnchor.PROTECT_BACKLINE,
                                    "anti-air coverage for backline",
                                )
                            ],
                            why_considered=(
                                "Enemy has air units — they bypass ground defenses."
                                " Add anti-air to protect backline."
                            ),
                            risks=["may sacrifice frontline investment"],
                        )
                    )

        # ── ANTI_CHAFF_CLEAR ──────────────────────────────────────────────────
        if "enemy_chaff_overload" in threat_map:
            t = threat_map["enemy_chaff_overload"]
            if t.my_answer != AnswerStrength.STRONG:
                ac_buy = _ids_for(ANTI_CHAFF_UNITS, buys)
                ac_unlock = _ids_for(ANTI_CHAFF_UNITS, unlocks)
                required = ac_unlock + ac_buy
                if required:
                    first = required[0]
                    bundles.append(
                        TacticalBundle(
                            id="bundle_anti_chaff",
                            theme=TacticalTheme.ANTI_CHAFF_CLEAR,
                            title="Anti-chaff clear",
                            target_threats=["enemy_chaff_overload"],
                            required_action_ids=required,
                            estimated_cost=_min_cost(ac_buy, legal_actions),
                            placement_intents=[
                                _intent(
                                    first,
                                    Lane.CENTER,
                                    Depth.MID_FRONT,
                                    PlacementAnchor.CENTER_COVERAGE,
                                    "splash coverage against chaff flood",
                                )
                            ],
                            why_considered=(
                                "Enemy has mass chaff — splash damage unit counters this."
                            ),
                            risks=["commits supply early; no single-target investment"],
                        )
                    )

        # ── ANTI_ARTILLERY_PRESSURE ───────────────────────────────────────────
        if "enemy_artillery_pressure" in threat_map:
            flank_buy = _ids_for(FLANK_UNITS, buys)
            flank_unlock = _ids_for(FLANK_UNITS, unlocks)
            required = flank_unlock + flank_buy
            if required:
                first = required[0]
                bundles.append(
                    TacticalBundle(
                        id="bundle_anti_artillery",
                        theme=TacticalTheme.ANTI_ARTILLERY_PRESSURE,
                        title="Answer enemy artillery",
                        target_threats=["enemy_artillery_pressure"],
                        required_action_ids=required,
                        optional_action_ids=move_ids[:2],
                        estimated_cost=_min_cost(flank_buy, legal_actions),
                        placement_intents=[
                            _intent(
                                first,
                                Lane.LEFT,
                                Depth.FRONT,
                                PlacementAnchor.FLANK_PRESSURE,
                                "flank to pressure enemy backline",
                                zone=flank_zone,
                            ),
                            _intent(
                                required[0],
                                Lane.RIGHT,
                                Depth.FRONT,
                                PlacementAnchor.FLANK_PRESSURE,
                                "secondary flank pressure",
                                zone=flank_zone,
                            ),
                        ],
                        why_considered=(
                            "Enemy backline artillery needs fast flankers to disrupt."
                        ),
                        risks=["commits to aggro line; enemy may pivot"],
                    )
                )

        # ── HEAVY_FRONTLINE_COUNTER ───────────────────────────────────────────
        if "enemy_frontline_wall" in threat_map:
            t = threat_map["enemy_frontline_wall"]
            if t.my_answer != AnswerStrength.STRONG:
                st_buy = _ids_for(_SINGLE_TARGET_UNITS, buys)
                st_unlock = _ids_for(_SINGLE_TARGET_UNITS, unlocks)
                required = st_unlock + st_buy
                if required:
                    first = required[0]
                    bundles.append(
                        TacticalBundle(
                            id="bundle_heavy_counter",
                            theme=TacticalTheme.HEAVY_FRONTLINE_COUNTER,
                            title="Heavy frontline counter",
                            target_threats=["enemy_frontline_wall"],
                            required_action_ids=required,
                            estimated_cost=_min_cost(st_buy, legal_actions),
                            placement_intents=[
                                _intent(
                                    first,
                                    Lane.CENTER,
                                    Depth.MID_FRONT,
                                    purpose="sustained single-target DPS vs heavy wall",
                                )
                            ],
                            why_considered=(
                                "Enemy heavy frontline needs single-target DPS to break."
                            ),
                            risks=["single-target is vulnerable to chaff distraction"],
                        )
                    )

        # ── TOWER_DEFENSE ─────────────────────────────────────────────────────
        construction_lost = "construction_lost" in threat_map
        tower_exposed = any("tower_exposure" in note for note in features.tower_notes)
        if construction_lost or tower_exposed:
            exposed_left = any(
                "tower_exposure_left" in note for note in features.tower_notes
            )
            lane = Lane.LEFT if exposed_left else Lane.RIGHT
            required = keep_ids[:2] + move_ids[:2]
            bundles.append(
                TacticalBundle(
                    id="bundle_tower_defense",
                    theme=TacticalTheme.TOWER_DEFENSE,
                    title="Tower defense",
                    target_threats=["construction_lost"],
                    required_action_ids=required,
                    estimated_cost=0,
                    placement_intents=[
                        PlacementIntent(
                            unit="frontline_unit",
                            action=PlacementAction.MOVE,
                            lane=lane,
                            depth=Depth.MID_BACK,
                            anchor=PlacementAnchor.PROTECT_TOWER,
                            purpose="protect exposed tower flank",
                        )
                    ],
                    why_considered=(
                        "Tower exposed or destroyed — reposition units to protect."
                    ),
                    risks=["defensive play may cede frontline pressure"],
                )
            )

        # ── FLANK_PRESSURE ────────────────────────────────────────────────────
        if "enemy_has_scaling_carry" in threat_map:
            flank_buy = _ids_for(FLANK_UNITS, buys)
            if flank_buy:
                first = flank_buy[0]
                bundles.append(
                    TacticalBundle(
                        id="bundle_flank_pressure",
                        theme=TacticalTheme.FLANK_PRESSURE,
                        title="Flank pressure to deny scaling",
                        target_threats=["enemy_has_scaling_carry"],
                        required_action_ids=flank_buy,
                        estimated_cost=_min_cost(flank_buy, legal_actions),
                        placement_intents=[
                            _intent(
                                first,
                                Lane.LEFT,
                                Depth.FRONT,
                                PlacementAnchor.FLANK_PRESSURE,
                                "close game before enemy scales",
                                zone=flank_zone,
                            )
                        ],
                        why_considered=(
                            "Enemy scaling carries get stronger each round — close the game now."
                        ),
                        risks=["early aggression fails if enemy has good frontline"],
                    )
                )

        # ── ECONOMY_SCALING ───────────────────────────────────────────────────
        high_threats = [t for t in features.threats if t.severity >= 0.6]
        if not high_threats:
            scale_buy = _ids_for(SCALING_UNITS, buys)
            if scale_buy:
                first = scale_buy[0]
                bundles.append(
                    TacticalBundle(
                        id="bundle_economy_scaling",
                        theme=TacticalTheme.ECONOMY_SCALING,
                        title="Economy scaling",
                        target_threats=[],
                        required_action_ids=scale_buy,
                        estimated_cost=_min_cost(scale_buy, legal_actions),
                        placement_intents=[
                            _intent(
                                first,
                                Lane.CENTER,
                                Depth.BACK,
                                anchor=PlacementAnchor.PROTECT_BACKLINE,
                                purpose="safe backline scaling position",
                            )
                        ],
                        why_considered=(
                            "No immediate threats — invest in long-term scaling."
                        ),
                        risks=["opponent may pivot aggressively next round"],
                    )
                )

        # ── TEMPO_RECOVERY ────────────────────────────────────────────────────
        if features.tempo_state == "behind":
            all_buy = [a.id for a in legal_actions if a.type == "buy_unit"]
            if all_buy:
                first = all_buy[0]
                bundles.append(
                    TacticalBundle(
                        id="bundle_tempo_recovery",
                        theme=TacticalTheme.TEMPO_RECOVERY,
                        title="Tempo recovery",
                        target_threats=[],
                        required_action_ids=all_buy[:3],
                        estimated_cost=_min_cost(all_buy[:3], legal_actions),
                        placement_intents=[
                            _intent(
                                first,
                                Lane.CENTER,
                                Depth.MID_FRONT,
                                purpose="add army value to recover tempo",
                            )
                        ],
                        why_considered=(
                            "Behind in army value — buy units to close the gap."
                        ),
                        risks=["buying wrong unit type may not solve the problem"],
                    )
                )

        # ── POSITIONING_FIX ───────────────────────────────────────────────────
        if "positioning_clump_risk" in threat_map:
            bundles.append(
                TacticalBundle(
                    id="bundle_positioning_fix",
                    theme=TacticalTheme.POSITIONING_FIX,
                    title="Spread units to reduce AoE risk",
                    target_threats=["positioning_clump_risk"],
                    required_action_ids=move_ids,
                    estimated_cost=0,
                    placement_intents=[
                        PlacementIntent(
                            unit="left_unit",
                            action=PlacementAction.MOVE,
                            lane=Lane.LEFT,
                            depth=Depth.MID,
                            purpose="spread left to reduce clump",
                        ),
                        PlacementIntent(
                            unit="right_unit",
                            action=PlacementAction.MOVE,
                            lane=Lane.RIGHT,
                            depth=Depth.MID,
                            purpose="spread right to reduce clump",
                        ),
                    ],
                    why_considered=(
                        "Units are tightly clustered — AoE units will shred them."
                    ),
                    risks=["spread units may lose mutual support"],
                )
            )

        # ── SAFE_DEFAULT ──────────────────────────────────────────────────────
        bundles.append(
            TacticalBundle(
                id="bundle_safe_default",
                theme=TacticalTheme.SAFE_DEFAULT,
                title="Hold position",
                target_threats=[],
                required_action_ids=(keep_ids[:4] or []) + ["skip"],
                estimated_cost=0,
                placement_intents=[],
                why_considered=(
                    "Safe fallback — maintain current army, spend supply carefully."
                ),
                risks=["no adaptation this round; opponent may pull ahead"],
            )
        )

        return bundles
