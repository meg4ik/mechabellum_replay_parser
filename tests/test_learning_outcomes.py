"""Tests for learning.outcomes — compute_outcome and OutcomeSummary (Phase 8)."""

from mechabellum_replay_parser.learning.outcomes import OutcomeSummary, compute_outcome
from mechabellum_replay_parser.coach.schemas import (
    ConstructionView,
    PlayerRoundView,
    StateView,
    StrategicMemory,
    UnitView,
)


def _state(
    round_: int,
    hp: int | None = None,
    fight_outcome: str | None = None,
    units: list | None = None,
    enemy_units: list | None = None,
    constructions: list | None = None,
) -> StateView:
    my_units = [UnitView(name=u) for u in (units or [])]
    enemy_unit_views = [UnitView(name=u) for u in (enemy_units or [])]
    return StateView(
        match_mode="VS_1_1",
        round=round_,
        player_name="P",
        enemy_names=["E"],
        my_state=PlayerRoundView(
            name="P",
            hp=hp,
            fight_outcome=fight_outcome,
            units=my_units,
            constructions=constructions or [],
        ),
        enemy_states=[PlayerRoundView(name="E", units=enemy_unit_views)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


# ── OutcomeSummary model ──────────────────────────────────────────────────────


def test_outcome_summary_defaults():
    o = OutcomeSummary(recommendation_id="r1", next_round_number=4)
    assert o.hp_delta is None
    assert o.fight_outcome_next_round is None
    assert o.tower_lost_next_round is None


def test_outcome_summary_full():
    o = OutcomeSummary(
        recommendation_id="r1",
        next_round_number=5,
        before_hp=20,
        next_round_hp=12,
        hp_delta=-8,
        fight_outcome_next_round="loss",
        units_survived_next_round=2,
        enemy_units_survived_next_round=4,
        tower_lost_next_round=True,
        player_followed_plan=False,
        notes="bad round",
    )
    assert o.hp_delta == -8
    assert o.fight_outcome_next_round == "loss"
    assert o.tower_lost_next_round is True


# ── compute_outcome HP ────────────────────────────────────────────────────────


def test_compute_outcome_hp_delta_negative():
    before = _state(3, hp=20)
    after = _state(4, hp=14)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.before_hp == 20
    assert outcome.next_round_hp == 14
    assert outcome.hp_delta == -6


def test_compute_outcome_hp_delta_positive():
    before = _state(3, hp=10)
    after = _state(4, hp=15)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.hp_delta == 5


def test_compute_outcome_hp_none_when_missing():
    before = _state(3, hp=None)
    after = _state(4, hp=None)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.hp_delta is None
    assert outcome.before_hp is None


def test_compute_outcome_hp_none_one_side():
    before = _state(3, hp=15)
    after = _state(4, hp=None)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.hp_delta is None


# ── fight_outcome ─────────────────────────────────────────────────────────────


def test_compute_outcome_fight_outcome_win():
    before = _state(3, hp=20)
    after = _state(4, hp=20, fight_outcome="win")
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.fight_outcome_next_round == "win"


def test_compute_outcome_fight_outcome_none():
    before = _state(3)
    after = _state(4)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.fight_outcome_next_round is None


# ── units survived ────────────────────────────────────────────────────────────


def test_compute_outcome_units_survived():
    before = _state(3, units=["arclight", "arclight", "fortress"])
    after = _state(4, units=["arclight"])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.units_survived_next_round == 1


def test_compute_outcome_enemy_units_survived():
    before = _state(3)
    after = _state(4, enemy_units=["crawler", "crawler", "crawler"])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.enemy_units_survived_next_round == 3


def test_compute_outcome_units_survived_zero():
    before = _state(3, units=["arclight"])
    after = _state(4, units=[])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.units_survived_next_round == 0


# ── tower_lost ────────────────────────────────────────────────────────────────


def test_compute_outcome_tower_lost_true():
    tower = ConstructionView(type="supply_tower", role="economy", status="alive")
    before = _state(3, constructions=[tower])
    after = _state(4, constructions=[])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.tower_lost_next_round is True


def test_compute_outcome_tower_not_lost():
    tower = ConstructionView(type="supply_tower", role="economy", status="alive")
    before = _state(3, constructions=[tower])
    after = _state(4, constructions=[tower])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.tower_lost_next_round is False


def test_compute_outcome_tower_none_when_no_constructions():
    before = _state(3, constructions=[])
    after = _state(4, constructions=[])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.tower_lost_next_round is None


def test_compute_outcome_destroyed_construction_counts_as_lost():
    tower_alive = ConstructionView(type="supply_tower", role="economy", status="alive")
    tower_dead = ConstructionView(type="supply_tower", role="economy", status="destroyed")
    before = _state(3, constructions=[tower_alive])
    after = _state(4, constructions=[tower_dead])
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.tower_lost_next_round is True


# ── player_followed_plan / notes ──────────────────────────────────────────────


def test_compute_outcome_player_followed_plan_passed_through():
    before = _state(3)
    after = _state(4)
    outcome = compute_outcome("rec_1", before, after, player_followed_plan=True)
    assert outcome.player_followed_plan is True


def test_compute_outcome_notes_passed_through():
    before = _state(3)
    after = _state(4)
    outcome = compute_outcome("rec_1", before, after, notes="bought wrong unit")
    assert outcome.notes == "bought wrong unit"


def test_compute_outcome_round_number_from_after_state():
    before = _state(5)
    after = _state(6)
    outcome = compute_outcome("rec_1", before, after)
    assert outcome.next_round_number == 6


def test_compute_outcome_recommendation_id():
    before = _state(1)
    after = _state(2)
    outcome = compute_outcome("rec_abc", before, after)
    assert outcome.recommendation_id == "rec_abc"
