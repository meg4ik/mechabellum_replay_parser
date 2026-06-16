"""Tests for LegalActionGenerator."""

import pytest

from mechabellum_replay_parser.coach.feature_extractor import FeatureExtractor
from mechabellum_replay_parser.coach.legal_actions import LegalActionGenerator
from mechabellum_replay_parser.coach.schemas import (
    PlayerRoundView,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    UnitView,
)


def _make_state(
    unlocked: list[str] = (),
    locked: list[str] = (),
    buys_remaining: int = 4,
    unlocks_remaining: int = 1,
    supply: int = 500,
    units: list[UnitView] = (),
    commander_skills: list[dict] = (),
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=supply,
        my_state=PlayerRoundView(
            name="Me",
            army_value=500,
            units=list(units),
            commander_skills=list(commander_skills),
            shop=ShopView(
                unlocked=list(unlocked),
                locked=list(locked),
                buys_remaining=buys_remaining,
                unlocks_remaining=unlocks_remaining,
            ),
        ),
        enemy_states=[PlayerRoundView(name="Enemy")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _no_threats() -> TacticalFeatures:
    return TacticalFeatures(
        threats=[],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )


def _threat(key: str, severity: float = 0.8) -> ThreatSignal:
    return ThreatSignal(key=key, severity=severity, explanation="test", source_units=[])


@pytest.fixture
def gen():
    return LegalActionGenerator()


# ── Unlock actions ────────────────────────────────────────────────────────────


def test_unlock_generated_when_locked_and_slots(gen):
    state = _make_state(locked=["phoenix"], unlocks_remaining=1)
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "unlock_phoenix" in ids


def test_no_unlock_when_zero_slots(gen):
    state = _make_state(locked=["phoenix"], unlocks_remaining=0)
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "unlock_phoenix" not in ids


def test_unlock_action_type(gen):
    state = _make_state(locked=["wasp"], unlocks_remaining=1)
    actions, _ = gen.generate(state, _no_threats())
    unlock = next(a for a in actions if a.id == "unlock_wasp")
    assert unlock.type == "unlock_unit"
    assert unlock.unit == "wasp"


# ── Buy actions ───────────────────────────────────────────────────────────────


def test_buy_generated_for_affordable_unit(gen):
    state = _make_state(unlocked=["crawler"], supply=200, buys_remaining=4)
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "buy_crawler" in ids


def test_buy_not_generated_when_too_expensive(gen):
    state = _make_state(unlocked=["fortress"], supply=50, buys_remaining=4)
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "buy_fortress" not in ids


def test_buy_not_generated_when_no_buys_remaining(gen):
    state = _make_state(unlocked=["crawler"], supply=500, buys_remaining=0)
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "buy_crawler" not in ids


def test_buy_cost_set_from_unit_data(gen):
    state = _make_state(unlocked=["marksmen"], supply=500, buys_remaining=4)
    actions, _ = gen.generate(state, _no_threats())
    buy = next(a for a in actions if a.id == "buy_marksmen")
    assert buy.cost == 100  # marksmen value from unit_data.json


def test_buy_with_unknown_cost_gets_tag(gen):
    # Use a unit not in unit_data.json (supply=9999 so it's not filtered by cost)
    state = _make_state(unlocked=["unknown_unit_xyz"], supply=9999, buys_remaining=4)
    actions, _ = gen.generate(state, _no_threats())
    buy = next((a for a in actions if a.id == "buy_unknown_unit_xyz"), None)
    assert buy is not None
    assert "cost_unknown" in buy.reason_tags


# ── Keep / Move actions ───────────────────────────────────────────────────────


def test_keep_and_move_generated_for_existing_unit(gen):
    state = _make_state(units=[UnitView(name="crawler", index=0)])
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "keep_crawler_0" in ids
    assert "move_crawler_0" in ids


def test_move_action_has_positions(gen):
    state = _make_state(units=[UnitView(name="crawler", index=0)])
    actions, _ = gen.generate(state, _no_threats())
    move = next(a for a in actions if a.id == "move_crawler_0")
    assert len(move.allowed_positions) > 0


def test_no_keep_move_without_units(gen):
    state = _make_state()
    actions, _ = gen.generate(state, _no_threats())
    types = {a.type for a in actions}
    assert "keep_unit" not in types
    assert "move_unit" not in types


# ── Skip ──────────────────────────────────────────────────────────────────────


def test_skip_always_present(gen):
    state = _make_state()
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "skip" in ids


# ── Commander skill actions ───────────────────────────────────────────────────


def test_skill_generated_when_ready(gen):
    state = _make_state(
        commander_skills=[
            {"name": "Airdrop", "is_active": False, "cooling_round": 1},
        ]
    )
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "skill_airdrop" in ids


def test_skill_not_generated_when_cooling(gen):
    state = _make_state(
        commander_skills=[
            {"name": "Airdrop", "is_active": False, "cooling_round": 10},
        ]
    )
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "skill_airdrop" not in ids


def test_skill_not_generated_when_active(gen):
    state = _make_state(
        commander_skills=[
            {"name": "Airdrop", "is_active": True, "cooling_round": 1},
        ]
    )
    actions, _ = gen.generate(state, _no_threats())
    ids = [a.id for a in actions]
    assert "skill_airdrop" not in ids


# ── Action groups ─────────────────────────────────────────────────────────────


def test_anti_air_group_when_air_threat(gen):
    state = _make_state(unlocked=["arclight"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_air_pressure")],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    ids = [g.id for g in groups]
    assert "anti_air_stabilization" in ids


def test_anti_air_group_contains_aa_buy(gen):
    state = _make_state(unlocked=["arclight", "mustang"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_air_pressure")],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    aa_group = next(g for g in groups if g.id == "anti_air_stabilization")
    unit_names = [a.unit for a in aa_group.actions]
    assert "arclight" in unit_names or "mustang" in unit_names


def test_anti_air_group_not_generated_without_threat(gen):
    state = _make_state(unlocked=["arclight"], supply=500, buys_remaining=4)
    _, groups = gen.generate(state, _no_threats())
    ids = [g.id for g in groups]
    assert "anti_air_stabilization" not in ids


def test_chaff_group_generated_on_chaff_threat(gen):
    state = _make_state(unlocked=["arclight"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_chaff_overload", 0.7)],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    ids = [g.id for g in groups]
    assert "anti_chaff_clear" in ids


def test_scaling_group_when_no_high_sev_threats(gen):
    state = _make_state(unlocked=["crawler", "fang"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_air_pressure", severity=0.3)],  # low severity
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="ahead",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    ids = [g.id for g in groups]
    assert "scaling_plan" in ids


def test_scaling_group_absent_with_high_sev_threat(gen):
    state = _make_state(unlocked=["crawler"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_air_pressure", severity=0.9)],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="behind",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    ids = [g.id for g in groups]
    assert "scaling_plan" not in ids


def test_group_addresses_threats_field(gen):
    state = _make_state(unlocked=["arclight"], supply=500, buys_remaining=4)
    features = TacticalFeatures(
        threats=[_threat("enemy_air_pressure")],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    _, groups = gen.generate(state, features)
    aa = next(g for g in groups if g.id == "anti_air_stabilization")
    assert "enemy_air_pressure" in aa.addresses_threats


# ── Integration with parsed_replay fixture ────────────────────────────────────


def test_generate_from_parsed_replay(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    builder = StateViewBuilder()
    gen = LegalActionGenerator()
    extractor = FeatureExtractor()

    state = builder.build(parsed_replay, supply=200, player_name="Player1")
    features = extractor.extract(state)
    actions, groups = gen.generate(state, features)

    # Minimal fixture: Player1 has crawler (unlocked in shop), 4 buys, 1 unlock
    action_types = {a.type for a in actions}
    assert "buy_unit" in action_types or "keep_unit" in action_types
    assert "skip" in {a.id for a in actions}
    assert isinstance(groups, list)
