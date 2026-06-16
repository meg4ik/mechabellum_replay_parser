"""Tests for eval case loading and saving (Phase 7)."""

from pathlib import Path

import pytest

from mechabellum_replay_parser.eval.cases import (
    EvalCase,
    EvalExpected,
    load_all_cases,
    load_case,
    save_case_from_debug,
)
from mechabellum_replay_parser.coach.schemas import (
    PlayerRoundView,
    ShopView,
    StateView,
    StrategicMemory,
)

_EVAL_CASES_DIR = Path(__file__).parent.parent / "eval_cases"


# ── EvalExpected model ────────────────────────────────────────────────────────


def test_eval_expected_defaults():
    expected = EvalExpected()
    assert not expected.must_address_threats
    assert not expected.acceptable_units


def test_eval_expected_with_threats():
    e = EvalExpected(
        must_address_threats=["enemy_air_pressure"],
        acceptable_units=["arclight"],
    )
    assert "enemy_air_pressure" in e.must_address_threats
    assert "arclight" in e.acceptable_units


# ── load_case ─────────────────────────────────────────────────────────────────


def test_load_case_air_threat():
    case_dir = _EVAL_CASES_DIR / "case_001_air_threat"
    case = load_case(case_dir)
    assert isinstance(case, EvalCase)
    assert case.name == "case_001_air_threat"
    assert case.state_view.round == 3
    assert "enemy_air_pressure" in case.expected.must_address_threats


def test_load_case_chaff_flood():
    case_dir = _EVAL_CASES_DIR / "case_002_chaff_flood"
    case = load_case(case_dir)
    assert "enemy_chaff_overload" in case.expected.must_address_threats


def test_load_case_tower_exposure():
    case_dir = _EVAL_CASES_DIR / "case_003_tower_exposure"
    case = load_case(case_dir)
    assert "construction_lost" in case.expected.must_address_threats


def test_load_case_missing_state_view(tmp_path):
    case_dir = tmp_path / "broken_case"
    case_dir.mkdir()
    (case_dir / "expected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="state_view.json"):
        load_case(case_dir)


def test_load_case_missing_expected(tmp_path):
    case_dir = tmp_path / "broken_case2"
    case_dir.mkdir()
    (case_dir / "state_view.json").write_text("{}", encoding="utf-8")
    with pytest.raises(Exception):
        load_case(case_dir)


# ── load_all_cases ────────────────────────────────────────────────────────────


def test_load_all_cases_returns_three():
    cases = load_all_cases(_EVAL_CASES_DIR)
    assert len(cases) >= 3


def test_load_all_cases_empty_dir(tmp_path):
    cases = load_all_cases(tmp_path)
    assert not cases


def test_load_all_cases_nonexistent_dir(tmp_path):
    cases = load_all_cases(tmp_path / "nonexistent")
    assert not cases


def test_load_all_cases_skips_broken(tmp_path):
    good_dir = tmp_path / "case_good"
    good_dir.mkdir()
    sv = StateView(
        match_mode="VS_1_1",
        round=1,
        player_name="P",
        enemy_names=["E"],
        my_state=PlayerRoundView(name="P"),
        enemy_states=[PlayerRoundView(name="E")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )
    (good_dir / "state_view.json").write_text(sv.model_dump_json(), encoding="utf-8")
    (good_dir / "expected.json").write_text(
        EvalExpected().model_dump_json(), encoding="utf-8"
    )

    broken_dir = tmp_path / "case_broken"
    broken_dir.mkdir()
    (broken_dir / "state_view.json").write_text("not valid json{{{", encoding="utf-8")
    (broken_dir / "expected.json").write_text("{}", encoding="utf-8")

    cases = load_all_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].state_view.round == 1


# ── save_case_from_debug ──────────────────────────────────────────────────────


def test_save_case_from_debug_creates_files(tmp_path):
    debug_dir = tmp_path / ".debug"
    debug_dir.mkdir()
    cases_dir = tmp_path / "eval_cases"

    sv = StateView(
        match_mode="VS_1_1",
        round=2,
        player_name="TestPlayer",
        enemy_names=["Opponent"],
        my_state=PlayerRoundView(
            name="TestPlayer",
            shop=ShopView(unlocked=["arclight"], locked=[], buys_remaining=3),
        ),
        enemy_states=[PlayerRoundView(name="Opponent")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )
    (debug_dir / "latest_state_view.json").write_text(
        sv.model_dump_json(indent=2), encoding="utf-8"
    )

    expected = EvalExpected(must_address_threats=["enemy_air_pressure"])
    case = save_case_from_debug(
        name="case_test",
        expected=expected,
        debug_dir=debug_dir,
        cases_dir=cases_dir,
        description="Test case",
    )

    assert isinstance(case, EvalCase)
    assert case.name == "case_test"
    assert (cases_dir / "case_test" / "state_view.json").exists()
    assert (cases_dir / "case_test" / "expected.json").exists()
    assert (cases_dir / "case_test" / "metadata.json").exists()


def test_save_case_from_debug_no_debug_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="state_view.json"):
        save_case_from_debug(
            name="x",
            expected=EvalExpected(),
            debug_dir=tmp_path / "nonexistent",
            cases_dir=tmp_path / "cases",
        )
