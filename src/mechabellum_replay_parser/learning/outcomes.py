"""Outcome computation from successive StateView snapshots."""

from __future__ import annotations

from pydantic import BaseModel

from ..coach.schemas import StateView


class OutcomeSummary(BaseModel):
    recommendation_id: str
    next_round_number: int
    before_hp: int | None = None
    next_round_hp: int | None = None
    hp_delta: int | None = None
    fight_outcome_next_round: str | None = None
    units_survived_next_round: int | None = None
    enemy_units_survived_next_round: int | None = None
    tower_lost_next_round: bool | None = None
    player_followed_plan: bool | None = None
    notes: str | None = None


def compute_outcome(
    recommendation_id: str,
    before_state: StateView,
    after_state: StateView,
    player_followed_plan: bool | None = None,
    notes: str | None = None,
) -> OutcomeSummary:
    before_hp = before_state.my_state.hp
    next_hp = after_state.my_state.hp
    hp_delta: int | None = None
    if before_hp is not None and next_hp is not None:
        hp_delta = next_hp - before_hp

    fight_outcome = after_state.my_state.fight_outcome

    units_survived = len(after_state.my_state.units)
    enemy_units_survived: int | None = None
    if after_state.enemy_states:
        enemy_units_survived = len(after_state.enemy_states[0].units)

    # Tower lost: count alive constructions before vs after
    before_alive = sum(
        1
        for c in before_state.my_state.constructions
        if getattr(c, "status", "alive") != "destroyed"
    )
    after_alive = sum(
        1
        for c in after_state.my_state.constructions
        if getattr(c, "status", "alive") != "destroyed"
    )
    tower_lost: bool | None = None
    if before_state.my_state.constructions or after_state.my_state.constructions:
        tower_lost = after_alive < before_alive

    return OutcomeSummary(
        recommendation_id=recommendation_id,
        next_round_number=after_state.round,
        before_hp=before_hp,
        next_round_hp=next_hp,
        hp_delta=hp_delta,
        fight_outcome_next_round=fight_outcome,
        units_survived_next_round=units_survived,
        enemy_units_survived_next_round=enemy_units_survived,
        tower_lost_next_round=tower_lost,
        player_followed_plan=player_followed_plan,
        notes=notes,
    )
