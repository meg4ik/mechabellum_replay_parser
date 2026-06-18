from __future__ import annotations

import json
from pathlib import Path

from .coordinates import CoordinateFrame
from .schemas import (
    LegalAction,
    PlanValidationResult,
    StateView,
    ValidationIssue,
)

_DATA_FILE = Path(__file__).parent.parent / "data" / "unit_data.json"
_UNIT_COSTS: dict[str, int] = {
    name: data["value"]
    for name, data in json.loads(_DATA_FILE.read_text(encoding="utf-8")).items()
}


class PlanValidator:
    """Validates a placement list from the LLM against the current StateView."""

    def validate_placement(
        self,
        placement: list[dict],
        state: StateView,
        legal_actions: list[LegalAction] | None = None,
    ) -> PlanValidationResult:
        issues: list[ValidationIssue] = []
        shop = state.my_state.shop
        unlocked: set[str] = set(shop.unlocked if shop else [])
        existing_units: dict[str, int] = {}
        for u in state.my_state.units:
            existing_units[u.name] = existing_units.get(u.name, 0) + 1

        frame = CoordinateFrame.from_units_and_constructions(
            state.my_state.units, state.my_state.constructions
        )
        y_lo = min(frame.front_y, frame.back_y)
        y_hi = max(frame.front_y, frame.back_y)

        opp_frame = frame.opponent_frame()
        opp_y_lo = min(opp_frame.front_y, opp_frame.back_y)
        opp_y_hi = max(opp_frame.front_y, opp_frame.back_y)

        buys_remaining = shop.buys_remaining if shop else None
        supply = state.my_supply
        new_count = sum(1 for p in placement if p.get("action") == "new")

        # ── Too many buys ─────────────────────────────────────────────────────
        if buys_remaining is not None and new_count > buys_remaining:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="too_many_buys",
                    message=(
                        f"Plan deploys {new_count} new unit(s) "
                        f"but buys_remaining={buys_remaining}."
                    ),
                )
            )

        # ── Supply budget ─────────────────────────────────────────────────────
        if supply is not None:
            total_cost = sum(
                _UNIT_COSTS.get(p.get("unit", ""), 0)
                for p in placement
                if p.get("action") == "new"
            )
            if total_cost > supply:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="supply_overspend",
                        message=(
                            f"Estimated cost of new units ({total_cost}) "
                            f"exceeds current supply ({supply}). "
                            "Costs are approximate — verify in game."
                        ),
                    )
                )

        # Track how many of each unit have been validated as "keep"/"move"
        keep_move_counts: dict[str, int] = {}

        for entry in placement:
            unit_name = entry.get("unit", "")
            action = entry.get("action", "keep")
            x = entry.get("x", 0)
            y = entry.get("y", 0)

            # ── Coordinate bounds ─────────────────────────────────────────────
            zone = entry.get("zone", "own")
            if not frame.x_min <= x <= frame.x_max:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="out_of_bounds_x",
                        message=(
                            f"{unit_name}: x={x} outside deployment zone "
                            f"[{frame.x_min}, {frame.x_max}]."
                        ),
                    )
                )
            if zone == "opponent":
                if state.round < 2:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="opponent_zone_round1",
                            message=(
                                f"{unit_name}: opponent zone placement "
                                f"not available in round {state.round}."
                            ),
                        )
                    )
                elif not opp_y_lo <= y <= opp_y_hi:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="out_of_bounds_y",
                            message=(
                                f"{unit_name}: y={y} outside opponent zone "
                                f"[{opp_y_lo}, {opp_y_hi}]."
                            ),
                        )
                    )
            elif not y_lo <= y <= y_hi:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="out_of_bounds_y",
                        message=(
                            f"{unit_name}: y={y} outside deployment zone "
                            f"[{y_lo}, {y_hi}]."
                        ),
                    )
                )

            if action == "new":
                # ── Locked unit buy ───────────────────────────────────────────
                if unit_name and unit_name not in unlocked:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="unit_not_unlocked",
                            message=(
                                f"Cannot buy '{unit_name}': not present in shop.unlocked."
                            ),
                        )
                    )

            elif action in ("keep", "move"):
                # ── Unit not in army ──────────────────────────────────────────
                keep_move_counts[unit_name] = keep_move_counts.get(unit_name, 0) + 1
                available = existing_units.get(unit_name, 0)
                if keep_move_counts[unit_name] > available:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            code="unit_not_found",
                            message=(
                                f"'{unit_name}' marked as '{action}' "
                                f"but only {available} in current army "
                                f"(reference #{keep_move_counts[unit_name]})."
                            ),
                        )
                    )

            else:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="unknown_action",
                        message=f"Unknown placement action '{action}' for '{unit_name}'.",
                    )
                )

        is_valid = not any(i.severity == "error" for i in issues)
        return PlanValidationResult(
            plan_id="placement",
            is_valid=is_valid,
            issues=issues,
        )
