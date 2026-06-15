"""Tests for Planner using LocalProvider (no real LLM)."""
import pytest

from mechabellum_replay_parser.coach.feature_extractor import FeatureExtractor
from mechabellum_replay_parser.coach.legal_actions import LegalActionGenerator
from mechabellum_replay_parser.coach.planner import Planner, _make_fallback_plan
from mechabellum_replay_parser.coach.schemas import (
    ActionGroup,
    CandidatePlan,
    PlayerRoundView,
    Position,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    UnitView,
)
from mechabellum_replay_parser.coach.state_view import StateViewBuilder
from mechabellum_replay_parser.llm.providers.local_provider import LocalProvider


def _make_state(
    supply: int = 300,
    units: list[UnitView] | None = None,
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=2,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=supply,
        my_state=PlayerRoundView(
            name="Me",
            army_value=600,
            units=units or [UnitView(name="crawler", index=0)],
            shop=ShopView(unlocked=["arclight"], locked=[], buys_remaining=3, unlocks_remaining=1),
        ),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=700)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _no_features() -> TacticalFeatures:
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


def _no_groups() -> list[ActionGroup]:
    return []


def _make_planner(json_response: dict) -> Planner:
    return Planner(LocalProvider(json_response=json_response), system_prompt="test system")


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_returns_candidate_plans():
    planner = _make_planner({
        "plans": [
            {
                "id": "plan_aa",
                "title": "Buy arclight",
                "action_ids": ["buy_arclight"],
                "total_cost": 100,
                "main_goal": "Counter air",
                "why_it_works": "Arclight has anti-air.",
                "risks": [],
                "expected_enemy_response": [],
                "placement": [{"unit": "arclight", "x": 0, "y": -100, "action": "new"}],
                "confidence": 0.7,
            }
        ]
    })
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert len(plans) == 1
    assert plans[0].id == "plan_aa"
    assert isinstance(plans[0], CandidatePlan)


@pytest.mark.anyio
async def test_multiple_plans_returned():
    planner = _make_planner({
        "plans": [
            {
                "id": "plan_1",
                "title": "Plan one",
                "action_ids": [],
                "total_cost": 0,
                "main_goal": "goal 1",
                "why_it_works": "works 1",
                "risks": [],
                "expected_enemy_response": [],
                "placement": [],
                "confidence": 0.5,
            },
            {
                "id": "plan_2",
                "title": "Plan two",
                "action_ids": [],
                "total_cost": 0,
                "main_goal": "goal 2",
                "why_it_works": "works 2",
                "risks": [],
                "expected_enemy_response": [],
                "placement": [],
                "confidence": 0.6,
            },
        ]
    })
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert len(plans) == 2


# ── Fallback on empty / malformed LLM response ────────────────────────────────

@pytest.mark.anyio
async def test_fallback_on_empty_plans():
    planner = _make_planner({"plans": []})
    state = _make_state()
    plans = await planner.generate_plans(state, _no_features(), _no_groups())
    assert len(plans) == 1
    assert plans[0].id == "plan_fallback"


@pytest.mark.anyio
async def test_fallback_on_missing_plans_key():
    planner = _make_planner({})
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert plans[0].id == "plan_fallback"


@pytest.mark.anyio
async def test_fallback_on_invalid_plan_shape():
    planner = _make_planner({
        "plans": [{"broken": True}]
    })
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert plans[0].id == "plan_fallback"


@pytest.mark.anyio
async def test_fallback_on_provider_exception():
    class FailingProvider:
        async def complete_json(self, _system, _user, schema=None, temperature=0.2):
            raise RuntimeError("Network error")

        def stream_text(self, _system, _user, temperature=0.2):
            async def _gen():
                yield ""
            return _gen()

    planner = Planner(FailingProvider(), system_prompt="test")
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert plans[0].id == "plan_fallback"


# ── Fallback plan content ─────────────────────────────────────────────────────

def test_fallback_plan_keeps_existing_units():
    state = _make_state(units=[
        UnitView(name="crawler", index=0, position=Position(x=-40, y=-80)),
    ])
    plan = _make_fallback_plan(state)
    assert plan.id == "plan_fallback"
    assert any(p["unit"] == "crawler" and p["action"] == "keep" for p in plan.placement)


def test_fallback_plan_zero_cost():
    state = _make_state()
    plan = _make_fallback_plan(state)
    assert plan.total_cost == 0


def test_fallback_plan_low_confidence():
    plan = _make_fallback_plan(_make_state())
    assert plan.confidence < 0.2


# ── Plan schema validation ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_invalid_plans_skipped_valid_kept():
    """Mix of valid and invalid plans — only valid ones returned."""
    planner = _make_planner({
        "plans": [
            {"broken": True},
            {
                "id": "plan_good",
                "title": "Good plan",
                "action_ids": [],
                "total_cost": 0,
                "main_goal": "goal",
                "why_it_works": "works",
                "risks": [],
                "expected_enemy_response": [],
                "placement": [],
                "confidence": 0.5,
            },
        ]
    })
    plans = await planner.generate_plans(_make_state(), _no_features(), _no_groups())
    assert len(plans) == 1
    assert plans[0].id == "plan_good"


# ── Integration with parsed_replay fixture ────────────────────────────────────

@pytest.mark.anyio
async def test_generate_plans_from_parsed_replay(parsed_replay):
    builder = StateViewBuilder()
    extractor = FeatureExtractor()
    gen = LegalActionGenerator()
    state = builder.build(parsed_replay, supply=200, player_name="Player1")
    features = extractor.extract(state)
    _, groups = gen.generate(state, features)

    planner = _make_planner({
        "plans": [{
            "id": "plan_keep",
            "title": "Hold position",
            "action_ids": ["keep_crawler_0"],
            "total_cost": 0,
            "main_goal": "Keep crawler in place",
            "why_it_works": "Stable opening.",
            "risks": [],
            "expected_enemy_response": [],
            "placement": [{"unit": "crawler", "x": -40, "y": -80, "action": "keep"}],
            "confidence": 0.5,
        }]
    })
    plans = await planner.generate_plans(state, features, groups)
    assert len(plans) >= 1
    assert plans[0].id == "plan_keep"
