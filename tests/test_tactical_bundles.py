"""Tests for TacticalBundleGenerator (Phase 4)."""

from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    AnswerStrength,
    Depth,
    Lane,
    LegalAction,
    PlayerRoundView,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalBundle,
    TacticalFeatures,
    TacticalTheme,
    ThreatSignal,
    ThreatUrgency,
    UnitView,
)
from mechabellum_replay_parser.coach.tactical_bundles import TacticalBundleGenerator


# ── Fixtures / helpers ────────────────────────────────────────────────────────


def _make_features(
    threats: list[ThreatSignal] | None = None,
    tower_notes: list[str] | None = None,
    tempo_state: str = "even",
) -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state=tempo_state,
        board_posture="standard",
        tower_notes=tower_notes or [],
        likely_enemy_continuation=[],
        priority_questions=[],
        my_army_profile=ArmyProfile(),
        enemy_army_profile=ArmyProfile(),
    )


def _make_state(units: list[UnitView] | None = None) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=600,
        my_state=PlayerRoundView(
            name="Me",
            army_value=500,
            units=units or [],
            shop=ShopView(
                buys_remaining=4,
                unlocks_remaining=1,
                unlocked=[
                    "arclight",
                    "mustang",
                    "vulcan",
                    "crawler",
                    "fortress",
                    "warfactory",
                    "marksmen",
                    "phoenix",
                    "fang",
                    "stormcaller",
                ],
                locked=["melting point"],
            ),
        ),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=500)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _make_legal_actions(
    buy_units: list[str],
    keep_units: list[str] | None = None,
    unlock_units: list[str] | None = None,
) -> list[LegalAction]:
    actions: list[LegalAction] = []
    unit_costs = {
        "arclight": 100,
        "mustang": 200,
        "vulcan": 400,
        "crawler": 100,
        "fortress": 400,
        "warfactory": 800,
        "marksmen": 100,
        "phoenix": 200,
        "fang": 100,
        "stormcaller": 200,
        "melting point": 400,
        "fire badger": 200,
        "scorpion": 300,
        "raiden": 400,
        "overlord": 500,
    }
    for u in buy_units:
        actions.append(
            LegalAction(
                id=f"buy_{u}", type="buy_unit", cost=unit_costs.get(u, 200), unit=u
            )
        )
    for u in unlock_units or []:
        actions.append(
            LegalAction(id=f"unlock_{u}", type="unlock_unit", cost=0, unit=u)
        )
    for u in keep_units or []:
        actions.append(LegalAction(id=f"keep_{u}_0", type="keep_unit", cost=0, unit=u))
        actions.append(
            LegalAction(
                id=f"move_{u}_0", type="move_unit", cost=0, unit=u, allowed_positions=[]
            )
        )
    actions.append(LegalAction(id="skip", type="skip", cost=0))
    return actions


def _threat(
    key: str, severity: float, answer: AnswerStrength = AnswerStrength.NONE
) -> ThreatSignal:
    return ThreatSignal(
        key=key,
        severity=severity,
        urgency=ThreatUrgency.HIGH,
        source_units=[],
        explanation="test",
        my_answer=answer,
    )


def _themes(bundles: list[TacticalBundle]) -> set[str]:
    return {b.theme for b in bundles}


# ── Safe default ──────────────────────────────────────────────────────────────


def test_safe_default_always_exists():
    gen = TacticalBundleGenerator()
    state = _make_state()
    features = _make_features()
    legal = _make_legal_actions([])
    bundles = gen.generate(state, features, legal)
    themes = _themes(bundles)
    assert TacticalTheme.SAFE_DEFAULT in themes


def test_at_least_one_bundle_always():
    gen = TacticalBundleGenerator()
    bundles = gen.generate(_make_state(), _make_features(), [])
    assert len(bundles) >= 1


# ── Air threat → anti-air bundle ──────────────────────────────────────────────


def test_air_threat_creates_anti_air_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["arclight", "mustang"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ANTI_AIR_RESPONSE in _themes(bundles)


def test_air_threat_no_bundle_if_answer_strong():
    gen = TacticalBundleGenerator()
    features = _make_features(
        threats=[_threat("enemy_air_pressure", 0.2, AnswerStrength.STRONG)]
    )
    legal = _make_legal_actions(["arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ANTI_AIR_RESPONSE not in _themes(bundles)


def test_anti_air_bundle_references_anti_air_actions():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["arclight", "mustang", "crawler"])
    bundles = gen.generate(_make_state(), features, legal)
    aa = next(b for b in bundles if b.theme == TacticalTheme.ANTI_AIR_RESPONSE)
    assert any("arclight" in aid or "mustang" in aid for aid in aa.required_action_ids)
    assert not any("crawler" in aid for aid in aa.required_action_ids)


def test_anti_air_bundle_has_placement_intent():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    aa = next(b for b in bundles if b.theme == TacticalTheme.ANTI_AIR_RESPONSE)
    assert len(aa.placement_intents) > 0


# ── Chaff threat → anti-chaff bundle ─────────────────────────────────────────


def test_chaff_threat_creates_anti_chaff_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_chaff_overload", 0.7)])
    legal = _make_legal_actions(["arclight", "vulcan"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ANTI_CHAFF_CLEAR in _themes(bundles)


def test_chaff_bundle_references_anti_chaff_units():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_chaff_overload", 0.7)])
    legal = _make_legal_actions(["arclight", "fortress"])
    bundles = gen.generate(_make_state(), features, legal)
    chaff = next(b for b in bundles if b.theme == TacticalTheme.ANTI_CHAFF_CLEAR)
    assert any("arclight" in aid for aid in chaff.required_action_ids)
    assert not any("fortress" in aid for aid in chaff.required_action_ids)


# ── Artillery threat → artillery response bundle ──────────────────────────────


def test_artillery_threat_creates_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_artillery_pressure", 0.5)])
    legal = _make_legal_actions(["crawler", "phoenix", "fang"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ANTI_ARTILLERY_PRESSURE in _themes(bundles)


def test_artillery_bundle_uses_flank_units():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_artillery_pressure", 0.5)])
    legal = _make_legal_actions(["crawler", "fortress"])
    bundles = gen.generate(_make_state(), features, legal)
    art = next(b for b in bundles if b.theme == TacticalTheme.ANTI_ARTILLERY_PRESSURE)
    assert any("crawler" in aid for aid in art.required_action_ids)
    assert not any("fortress" in aid for aid in art.required_action_ids)


# ── Tower exposure → tower defense bundle ─────────────────────────────────────


def test_tower_exposure_creates_tower_defense_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(
        tower_notes=["tower_exposure_right: supply_tower at x=150 may be flanked."]
    )
    legal = _make_legal_actions([], keep_units=["fortress"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.TOWER_DEFENSE in _themes(bundles)


def test_construction_lost_creates_tower_defense_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("construction_lost", 0.6)])
    legal = _make_legal_actions([], keep_units=["rhino"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.TOWER_DEFENSE in _themes(bundles)


# ── Bundle placement intents use valid lane/depth ─────────────────────────────


def test_placement_intents_use_valid_lane_and_depth():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    for bundle in bundles:
        for intent in bundle.placement_intents:
            assert isinstance(intent.lane, Lane)
            assert isinstance(intent.depth, Depth)


# ── Bundle references threat keys ─────────────────────────────────────────────


def test_bundle_target_threats_match_trigger():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    aa = next(b for b in bundles if b.theme == TacticalTheme.ANTI_AIR_RESPONSE)
    assert "enemy_air_pressure" in aa.target_threats


# ── No buy actions available → no theme bundle (except default) ───────────────


def test_no_buy_actions_no_anti_air_bundle():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions([])  # no buys available
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ANTI_AIR_RESPONSE not in _themes(bundles)
    assert TacticalTheme.SAFE_DEFAULT in _themes(bundles)


# ── Economy scaling when no threats ──────────────────────────────────────────


def test_economy_scaling_when_no_threats():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[])
    legal = _make_legal_actions(["warfactory"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ECONOMY_SCALING in _themes(bundles)


def test_no_economy_scaling_when_high_threat():
    gen = TacticalBundleGenerator()
    features = _make_features(threats=[_threat("enemy_air_pressure", 0.9)])
    legal = _make_legal_actions(["warfactory", "arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.ECONOMY_SCALING not in _themes(bundles)


# ── Tempo recovery when behind ────────────────────────────────────────────────


def test_tempo_recovery_when_behind():
    gen = TacticalBundleGenerator()
    features = _make_features(tempo_state="behind")
    legal = _make_legal_actions(["arclight"])
    bundles = gen.generate(_make_state(), features, legal)
    assert TacticalTheme.TEMPO_RECOVERY in _themes(bundles)
