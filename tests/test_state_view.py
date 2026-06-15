"""Tests for StateViewBuilder."""
import pytest

from mechabellum_replay_parser.coach.schemas import (
    ConstructionView,
    PlayerRoundView,
    StateView,
    StrategicMemory,
    UnitView,
)
from mechabellum_replay_parser.coach.state_view import StateViewBuilder


@pytest.fixture
def builder():
    return StateViewBuilder()


# ── Basic build ───────────────────────────────────────────────────────────────

def test_build_returns_state_view(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=100, player_name="Player1")
    assert isinstance(state, StateView)


def test_round_and_player_name(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=100, player_name="Player1")
    assert state.round == 1
    assert state.player_name == "Player1"


def test_match_mode(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=100, player_name="Player1")
    assert state.match_mode == "VS_2_2"


def test_supply_override(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=250, player_name="Player1")
    assert state.my_supply == 250
    assert state.my_state.supply == 250


def test_supply_none(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=None, player_name="Player1")
    assert state.my_supply is None
    assert state.my_state.supply is None


# ── Teams / enemies ───────────────────────────────────────────────────────────

def test_enemy_names_detected(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.enemy_names == ["Player2"]


def test_enemy_state_present(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert len(state.enemy_states) == 1
    assert state.enemy_states[0].name == "Player2"


def test_enemy_perspective(builder, parsed_replay):
    """Building from the other player's perspective swaps teams."""
    state = builder.build(parsed_replay, supply=0, player_name="Player2")
    assert state.enemy_names == ["Player1"]
    assert state.my_state.name == "Player2"


# ── Units ─────────────────────────────────────────────────────────────────────

def test_my_units_parsed(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert len(state.my_state.units) == 1
    assert state.my_state.units[0].name == "crawler"


def test_unit_has_position(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    pos = state.my_state.units[0].position
    assert pos is not None
    assert pos.x == -40
    assert pos.y == -80


def test_enemy_has_no_units(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.enemy_states[0].units == []


# ── Constructions ─────────────────────────────────────────────────────────────

def test_my_constructions_parsed(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert len(state.my_state.constructions) == 1
    c = state.my_state.constructions[0]
    assert isinstance(c, ConstructionView)
    assert c.position is not None
    assert c.position.x == 100
    assert c.position.y == -270


def test_enemy_has_no_constructions(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.enemy_states[0].constructions == []


# ── Shop ──────────────────────────────────────────────────────────────────────

def test_shop_buys_remaining(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.my_state.shop is not None
    assert state.my_state.shop.buys_remaining == 4


def test_shop_unlocks_remaining(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.my_state.shop.unlocks_remaining == 1


# ── Round summaries ───────────────────────────────────────────────────────────

def test_recent_rounds_count(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert len(state.recent_rounds) == 1


def test_recent_round_outcome(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    summary = state.recent_rounds[0]
    assert summary.round == 1
    assert summary.my_outcome == "win"
    assert summary.enemy_outcome == "loss"


# ── Strategic memory ──────────────────────────────────────────────────────────

def test_strategic_memory_type(builder, parsed_replay):
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert isinstance(state.strategic_memory, StrategicMemory)


def test_strategic_memory_no_events_single_round(builder, parsed_replay):
    """Only 1 round available → no new-unit events (nothing to compare against)."""
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.strategic_memory.critical_events == []


def test_strategic_memory_repeated_investment_single_round(builder, parsed_replay):
    """A unit seen in only 1 round should NOT appear in do_not_forget."""
    state = builder.build(parsed_replay, supply=0, player_name="Player1")
    assert state.strategic_memory.do_not_forget == []


def test_strategic_memory_multi_round():
    """Synthetic 2-round parsed dict — crawler seen both rounds triggers do_not_forget."""
    builder = StateViewBuilder()
    parsed = {
        "metadata": {"match_mode": "VS_1_1"},
        "teams": [["Me"], ["Enemy"]],
        "last_round": 2,
        "rounds": [
            {
                "round": 1,
                "fight_result": None,
                "players": {
                    "Me": {"units": [], "constructions": [], "fight_outcome": "loss",
                            "active_techs": [], "shop": {}, "army_value": 100,
                            "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                            "contraptions": []},
                    "Enemy": {"units": [{"name": "crawler", "unit_id": 10, "index": 0,
                                          "level": 1, "exp": 0, "rounds_survived": 0,
                                          "position": {"x": 0, "y": 80}, "equipment": None,
                                          "sell_supply": 60, "rotate": False}],
                               "constructions": [], "fight_outcome": "win",
                               "active_techs": [], "shop": {}, "army_value": 100,
                               "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                               "contraptions": []},
                },
            },
            {
                "round": 2,
                "fight_result": None,
                "players": {
                    "Me": {"units": [], "constructions": [], "fight_outcome": None,
                            "active_techs": [], "shop": {}, "army_value": 100,
                            "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                            "contraptions": []},
                    "Enemy": {"units": [{"name": "crawler", "unit_id": 10, "index": 0,
                                          "level": 1, "exp": 0, "rounds_survived": 1,
                                          "position": {"x": 0, "y": 80}, "equipment": None,
                                          "sell_supply": 60, "rotate": False}],
                               "constructions": [], "fight_outcome": None,
                               "active_techs": [], "shop": {}, "army_value": 100,
                               "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                               "contraptions": []},
                },
            },
        ],
    }
    state = builder.build(parsed, supply=None, player_name="Me")
    assert any("crawler" in note for note in state.strategic_memory.do_not_forget)


def test_strategic_memory_new_enemy_unit_event():
    """Enemy adds phoenix in round 2 → critical_events contains that."""
    builder = StateViewBuilder()
    parsed = {
        "metadata": {"match_mode": "VS_1_1"},
        "teams": [["Me"], ["Enemy"]],
        "last_round": 2,
        "rounds": [
            {
                "round": 1,
                "fight_result": None,
                "players": {
                    "Me": {"units": [], "constructions": [], "fight_outcome": "loss",
                            "active_techs": [], "shop": {}, "army_value": 0,
                            "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                            "contraptions": []},
                    "Enemy": {"units": [],
                               "constructions": [], "fight_outcome": "win",
                               "active_techs": [], "shop": {}, "army_value": 0,
                               "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                               "contraptions": []},
                },
            },
            {
                "round": 2,
                "fight_result": None,
                "players": {
                    "Me": {"units": [], "constructions": [], "fight_outcome": None,
                            "active_techs": [], "shop": {}, "army_value": 0,
                            "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                            "contraptions": []},
                    "Enemy": {"units": [{"name": "phoenix", "unit_id": 16, "index": 0,
                                          "level": 1, "exp": 0, "rounds_survived": 0,
                                          "position": {"x": 0, "y": 80}, "equipment": None,
                                          "sell_supply": 120, "rotate": False}],
                               "constructions": [], "fight_outcome": None,
                               "active_techs": [], "shop": {}, "army_value": 200,
                               "hp": 3, "supply": 0, "officers": [], "commander_skills": [],
                               "contraptions": []},
                },
            },
        ],
    }
    state = builder.build(parsed, supply=None, player_name="Me")
    assert any("phoenix" in e and "round 2" in e for e in state.strategic_memory.critical_events)
