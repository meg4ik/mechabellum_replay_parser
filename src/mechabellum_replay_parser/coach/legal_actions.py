from __future__ import annotations

import json
from pathlib import Path

from .feature_extractor import (
    AIR_UNITS,
    ANTI_AIR_UNITS,
    ANTI_CHAFF_UNITS,
)
from .schemas import ActionGroup, LegalAction, StateView, TacticalFeatures

_DATA_FILE = Path(__file__).parent.parent / "data" / "unit_data.json"
_UNIT_COSTS: dict[str, int | None] = {
    name: data.get("value")
    for name, data in json.loads(_DATA_FILE.read_text(encoding="utf-8")).items()
}

# Strategic position slots offered to the LLM for unit movement.
_STRATEGIC_POSITIONS = [
    {"label": "front_center", "x": 0, "y": -60},
    {"label": "mid_center", "x": 0, "y": -150},
    {"label": "back_center", "x": 0, "y": -260},
    {"label": "left_flank", "x": -220, "y": -100},
    {"label": "right_flank", "x": 220, "y": -100},
    {"label": "protect_tower", "x": 100, "y": -270},
    {"label": "anti_flank", "x": -200, "y": -200},
]

_OPPONENT_FLANK_POSITIONS = [
    {"label": "opp_left_flank", "x": -220, "y": 60, "zone": "opponent"},
    {"label": "opp_right_flank", "x": 220, "y": 60, "zone": "opponent"},
    {"label": "opp_center_front", "x": 0, "y": 60, "zone": "opponent"},
]

_FAST_FLANKER_UNITS = frozenset({"mustang", "sabertooth", "phoenix", "wasp"})


class LegalActionGenerator:
    def generate(
        self,
        state: StateView,
        features: TacticalFeatures,
    ) -> tuple[list[LegalAction], list[ActionGroup]]:
        actions: list[LegalAction] = []
        shop = state.my_state.shop
        supply = state.my_supply or 0
        buys_remaining = (shop.buys_remaining if shop else None) or 0
        unlocks_remaining = (shop.unlocks_remaining if shop else None) or 0
        unlocked = set(shop.unlocked if shop else [])
        locked = set(shop.locked if shop else [])

        # ── Unlock unit ───────────────────────────────────────────────────────
        if unlocks_remaining > 0:
            for unit_name in sorted(locked):
                actions.append(
                    LegalAction(
                        id=f"unlock_{unit_name}",
                        type="unlock_unit",
                        cost=0,
                        unit=unit_name,
                        reason_tags=["available_in_shop"],
                    )
                )

        # ── Buy unit ──────────────────────────────────────────────────────────
        if buys_remaining > 0:
            for unit_name in sorted(unlocked):
                raw_cost = _UNIT_COSTS.get(unit_name)
                cost: int = raw_cost if raw_cost is not None else 0
                tags: list[str] = []
                if raw_cost is None or cost == 0:
                    tags.append("cost_unknown")
                elif cost > supply:
                    continue
                actions.append(
                    LegalAction(
                        id=f"buy_{unit_name}",
                        type="buy_unit",
                        cost=cost,
                        unit=unit_name,
                        reason_tags=tags,
                    )
                )

        # ── Keep / Move existing units ────────────────────────────────────────
        move_positions = list(_STRATEGIC_POSITIONS)
        if state.round >= 2:
            move_positions += _OPPONENT_FLANK_POSITIONS

        for unit in state.my_state.units:
            idx = unit.index if unit.index is not None else 0
            actions.append(
                LegalAction(
                    id=f"keep_{unit.name}_{idx}",
                    type="keep_unit",
                    cost=0,
                    unit=unit.name,
                    unit_index=unit.index,
                )
            )
            actions.append(
                LegalAction(
                    id=f"move_{unit.name}_{idx}",
                    type="move_unit",
                    cost=0,
                    unit=unit.name,
                    unit_index=unit.index,
                    allowed_positions=move_positions,
                )
            )

        # ── Commander skills ──────────────────────────────────────────────────
        for skill in state.my_state.commander_skills:
            name = skill.get("name", "")
            is_active = skill.get("is_active", False)
            cooling = skill.get("cooling_round", 999)
            if not is_active and cooling <= state.round:
                safe_id = name.replace(" ", "_").lower()
                actions.append(
                    LegalAction(
                        id=f"skill_{safe_id}",
                        type="use_skill",
                        cost=0,
                        reason_tags=["commander_skill"],
                        constraints=[f"skill_name:{name}"],
                    )
                )

        # ── Skip ──────────────────────────────────────────────────────────────
        actions.append(LegalAction(id="skip", type="skip", cost=0))

        # ── Action groups ─────────────────────────────────────────────────────
        groups = self._make_groups(actions, features)
        return actions, groups

    # ── Group construction ────────────────────────────────────────────────────

    def _make_groups(
        self,
        actions: list[LegalAction],
        features: TacticalFeatures,
    ) -> list[ActionGroup]:
        groups: list[ActionGroup] = []
        threat_keys = {t.key for t in features.threats}
        buy_actions = [a for a in actions if a.type == "buy_unit"]
        unlock_actions = [a for a in actions if a.type == "unlock_unit"]

        # Anti-air stabilization
        if "enemy_air_pressure" in threat_keys:
            aa_buy = [a for a in buy_actions if a.unit in ANTI_AIR_UNITS]
            aa_unlock = [a for a in unlock_actions if a.unit in ANTI_AIR_UNITS]
            group_actions = aa_unlock + aa_buy
            if group_actions:
                groups.append(
                    ActionGroup(
                        id="anti_air_stabilization",
                        title="Anti-air stabilization",
                        purpose="Counter enemy air units that bypass ground defenses",
                        actions=group_actions,
                        total_cost=min((a.cost for a in aa_buy), default=0),
                        addresses_threats=["enemy_air_pressure"],
                        risks=["may sacrifice frontline investment"],
                    )
                )

        # Anti-chaff clear
        if "enemy_chaff_overload" in threat_keys:
            ac_buy = [a for a in buy_actions if a.unit in ANTI_CHAFF_UNITS]
            if ac_buy:
                groups.append(
                    ActionGroup(
                        id="anti_chaff_clear",
                        title="Anti-chaff clear",
                        purpose="Splash damage to neutralise enemy chaff overload",
                        actions=ac_buy,
                        total_cost=min(a.cost for a in ac_buy),
                        addresses_threats=["enemy_chaff_overload"],
                    )
                )

        # Artillery / backline answer
        if "enemy_artillery_pressure" in threat_keys:
            fast_buy = [
                a for a in buy_actions if a.unit in _FAST_FLANKER_UNITS | AIR_UNITS
            ]
            if fast_buy:
                groups.append(
                    ActionGroup(
                        id="artillery_answer",
                        title="Answer enemy artillery",
                        purpose="Fast or flanking units to pressure the enemy backline",
                        actions=fast_buy,
                        total_cost=min(a.cost for a in fast_buy),
                        addresses_threats=["enemy_artillery_pressure"],
                        risks=["commits to aggro line; enemy may pivot"],
                    )
                )

        # Scaling plan — when no high-severity threats
        high_sev = [t for t in features.threats if t.severity >= 0.7]
        if not high_sev and buy_actions:
            groups.append(
                ActionGroup(
                    id="scaling_plan",
                    title="Scaling plan",
                    purpose="No immediate lethal threat — invest in long-term army strength",
                    actions=buy_actions[:6],
                    total_cost=0,
                    addresses_threats=[],
                )
            )

        return groups
