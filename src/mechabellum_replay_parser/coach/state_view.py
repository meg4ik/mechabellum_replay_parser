from __future__ import annotations

from .constructions import normalize_construction
from .coordinates import CoordinateFrame
from .schemas import (
    PlayerRoundView,
    Position,
    RoundSummary,
    ShopView,
    StateView,
    StrategicMemory,
    UnitView,
)

_UNIT_LOOKUP: dict[int, str] = {
    1: "fortress", 2: "marksmen", 3: "vulcan", 4: "melting point", 5: "rhino",
    6: "wasp", 7: "mustang", 8: "steel ball", 9: "fang", 10: "crawler",
    11: "overlord", 12: "stormcaller", 13: "sledgehammer", 14: "hacker",
    15: "arclight", 16: "phoenix", 17: "warfactory", 18: "wraith",
    19: "scorpion", 20: "fire badger", 21: "sabertooth", 22: "typhoon",
    23: "sandworm", 24: "tarantula", 25: "phantom ray", 26: "farseer",
    27: "raiden", 28: "hound", 29: "abyss", 30: "void eye", 31: "vortex",
}

_RECENT_ROUNDS = 3


class StateViewBuilder:
    def build(self, parsed: dict, supply: int | None, player_name: str) -> StateView:
        rounds: list[dict] = parsed.get("rounds", [])
        last_round: int = parsed.get("last_round", 0)
        teams: list[list[str]] = parsed.get("teams", [])
        match_mode: str | None = parsed.get("metadata", {}).get("match_mode")

        current_round = next(
            (r for r in rounds if r["round"] == last_round),
            rounds[-1] if rounds else {},
        )
        players_data: dict[str, dict] = current_round.get("players", {})

        enemy_team: list[str] = next((t for t in teams if player_name not in t), [])

        prev_round = next(
            (r for r in rounds if r["round"] == last_round - 1),
            None,
        )
        prev_unit_keys: set[tuple[str, int]] = set()
        if prev_round:
            for u in prev_round.get("players", {}).get(player_name, {}).get("units", []):
                prev_unit_keys.add((u.get("name", ""), u.get("index", 0)))

        my_raw = players_data.get(player_name, {})
        my_state = self._build_player_view(player_name, my_raw, prev_unit_keys)
        my_state.supply = supply  # override with manually entered value

        reinforcement_units = self._extract_reinforcement_units(my_raw, my_state.units)
        if reinforcement_units:
            my_state.units.extend(reinforcement_units)

        enemy_states = [
            self._build_player_view(name, players_data.get(name, {}))
            for name in enemy_team
        ]

        sorted_rounds = sorted(rounds, key=lambda r: r["round"])
        recent = sorted_rounds[-_RECENT_ROUNDS:]
        round_summaries = [
            self._build_round_summary(r, player_name, enemy_team) for r in recent
        ]

        strategic_memory = self._build_strategic_memory(
            sorted_rounds, player_name, enemy_team, last_round
        )

        return StateView(
            match_mode=match_mode,
            round=last_round,
            player_name=player_name,
            enemy_names=enemy_team,
            my_supply=supply,
            my_state=my_state,
            enemy_states=enemy_states,
            recent_rounds=round_summaries,
            strategic_memory=strategic_memory,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_player_view(
        self,
        name: str,
        raw: dict,
        prev_unit_keys: set[tuple[str, int]] | None = None,
    ) -> PlayerRoundView:
        tech_by_unit: dict[str, list[str]] = {}
        for t in raw.get("active_techs", []):
            uname = t.get("unit") or ""
            tname = t.get("tech") or ""
            if uname and tname:
                tech_by_unit.setdefault(uname, []).append(tname)

        units = []
        for u in raw.get("units", []):
            unit_key = (u.get("name", ""), u.get("index", 0))
            is_new = unit_key not in prev_unit_keys if prev_unit_keys else True
            units.append(
                UnitView(
                    name=u.get("name", ""),
                    unit_id=u.get("unit_id"),
                    index=u.get("index"),
                    level=u.get("level"),
                    exp=u.get("exp"),
                    rounds_survived=u.get("rounds_survived"),
                    position=Position(**u["position"]) if u.get("position") else None,
                    equipment=u.get("equipment"),
                    sell_supply=u.get("sell_supply"),
                    rotate=u.get("rotate"),
                    active_techs=tech_by_unit.get(u.get("name", ""), []),
                    is_new=is_new,
                )
            )

        # Two-pass: detect side from units + construction positions, then label.
        temp_constructions = [
            normalize_construction(c) for c in raw.get("constructions", [])
        ]
        frame = CoordinateFrame.from_units_and_constructions(units, temp_constructions)
        constructions = [
            normalize_construction(c, frame) for c in raw.get("constructions", [])
        ]

        shop_raw = raw.get("shop") or {}
        shop = ShopView(
            unlocked=shop_raw.get("unlocked") or [],
            locked=shop_raw.get("locked") or [],
            buys_remaining=shop_raw.get("buys_remaining"),
            unlocks_remaining=shop_raw.get("unlocks_remaining"),
        )

        return PlayerRoundView(
            name=name,
            hp=raw.get("hp"),
            supply=raw.get("supply"),
            army_value=raw.get("army_value"),
            fight_outcome=raw.get("fight_outcome"),
            officers=raw.get("officers") or [],
            commander_skills=raw.get("commander_skills") or [],
            units=units,
            constructions=constructions,
            contraptions=raw.get("contraptions") or [],
            shop=shop,
        )

    def _extract_reinforcement_units(
        self,
        raw: dict,
        existing_units: list[UnitView],
    ) -> list[UnitView]:
        """Detect units granted by reinforcement card_select actions not yet in units list."""
        actions = raw.get("actions", [])
        existing_names = {u.name.lower() for u in existing_units}
        max_index = max((u.index or 0 for u in existing_units), default=-1)

        reinforcement_units: list[UnitView] = []
        for action in actions:
            if action.get("type") != "card_select":
                continue
            card_id = action.get("card_id")
            if card_id is None:
                continue
            unit_id = card_id % 100
            unit_name = _UNIT_LOOKUP.get(unit_id)
            if unit_name is None:
                continue
            if unit_name.lower() in existing_names:
                continue
            max_index += 1
            reinforcement_units.append(
                UnitView(
                    name=unit_name,
                    unit_id=unit_id,
                    index=max_index,
                    level=0,
                    position=Position(x=0, y=-160),
                    is_new=True,
                )
            )
        return reinforcement_units

    def _build_round_summary(
        self,
        rnd: dict,
        player_name: str,
        enemy_names: list[str],
    ) -> RoundSummary:
        players = rnd.get("players", {})
        my_data = players.get(player_name, {})
        enemy_name = enemy_names[0] if enemy_names else ""
        enemy_data = players.get(enemy_name, {})
        enemy_av = sum(players.get(e, {}).get("army_value") or 0 for e in enemy_names)
        return RoundSummary(
            round=rnd["round"],
            my_outcome=my_data.get("fight_outcome"),
            enemy_outcome=enemy_data.get("fight_outcome"),
            my_army_value=my_data.get("army_value"),
            enemy_army_value=enemy_av,
        )

    def _build_strategic_memory(
        self,
        sorted_rounds: list[dict],
        player_name: str,
        enemy_names: list[str],
        last_round: int,
    ) -> StrategicMemory:
        critical_events: list[str] = []
        do_not_forget: list[str] = []

        # Build per-round enemy unit-type sets and my construction sets
        enemy_unit_history: dict[int, set[str]] = {}
        my_construction_history: dict[int, set[tuple]] = {}

        for rnd in sorted_rounds:
            rnum = rnd["round"]
            players = rnd.get("players", {})

            etypes: set[str] = set()
            for ename in enemy_names:
                for u in players.get(ename, {}).get("units", []):
                    if u.get("name"):
                        etypes.add(u["name"])
            enemy_unit_history[rnum] = etypes

            cset: set[tuple] = set()
            for c in players.get(player_name, {}).get("constructions", []):
                pos = c.get("position") or {}
                cset.add((c.get("type", ""), pos.get("x"), pos.get("y")))
            my_construction_history[rnum] = cset

        round_nums = sorted(enemy_unit_history)

        # New enemy unit types (skip first round — everything starts new)
        if len(round_nums) > 1:
            prev_types = enemy_unit_history[round_nums[0]]
            for rnum in round_nums[1:]:
                current = enemy_unit_history[rnum]
                for utype in sorted(current - prev_types):
                    critical_events.append(f"Enemy added {utype} in round {rnum}.")
                prev_types = current

        # Construction disappearance
        for i, rnum in enumerate(round_nums[1:], start=1):
            prev_rnum = round_nums[i - 1]
            disappeared = (
                my_construction_history[prev_rnum] - my_construction_history[rnum]
            )
            for ctype, cx, cy in sorted(disappeared):
                critical_events.append(
                    f"{ctype} at ({cx}, {cy}) disappeared after round {prev_rnum}."
                )

        # Repeated enemy investment (2+ rounds with same unit type)
        all_enemy_types: set[str] = set()
        for types in enemy_unit_history.values():
            all_enemy_types |= types

        for utype in sorted(all_enemy_types):
            rounds_present = sum(
                1 for types in enemy_unit_history.values() if utype in types
            )
            if rounds_present >= 2:
                do_not_forget.append(
                    f"Enemy has been investing in {utype} for {rounds_present} round(s)."
                )

        return StrategicMemory(
            critical_events=critical_events,
            do_not_forget=do_not_forget,
        )
