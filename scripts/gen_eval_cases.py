"""Generate 10 eval cases for influence map testing."""

import json
from pathlib import Path

from mechabellum_replay_parser.coach.schemas import (
    ConstructionRole,
    ConstructionType,
    ConstructionView,
    PlayerRoundView,
    Position,
    ShopView,
    StateView,
    StrategicMemory,
    UnitView,
)

CASES_DIR = Path("eval_cases")


def _unit(name, x=0, y=-100, level=1, index=0, techs=None):
    return UnitView(
        name=name, unit_id=0, index=index, level=level, exp=0,
        position=Position(x=x, y=y), active_techs=techs or [],
    )


def _state(my_units=None, enemy_units=None, supply=600, round_num=4, constructions=None):
    return StateView(
        match_mode="VS_1_1", round=round_num, player_name="Player1",
        enemy_names=["Player2"], my_supply=supply,
        my_state=PlayerRoundView(
            name="Player1", hp=3, army_value=500,
            units=my_units or [], constructions=constructions or [],
            shop=ShopView(
                unlocked=["crawler", "arclight", "mustang", "marksmen", "vulcan"],
                locked=["phoenix", "overlord"],
                buys_remaining=3, unlocks_remaining=1,
            ),
        ),
        enemy_states=[
            PlayerRoundView(name="Player2", hp=3, army_value=500, units=enemy_units or []),
        ],
        recent_rounds=[], strategic_memory=StrategicMemory(),
    )


def save(name, state, expected, desc=""):
    d = CASES_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "state_view.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    (d / "expected.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")
    (d / "metadata.json").write_text(
        json.dumps({"name": name, "description": desc}, indent=2), encoding="utf-8",
    )


# 1. Anti-air gap
save(
    "case_001_air_threat",
    _state(
        my_units=[_unit("crawler", x=0, y=-100), _unit("crawler", x=-100, y=-100, index=1)],
        enemy_units=[
            _unit("wasp", x=0, y=-30, level=2),
            _unit("wasp", x=100, y=-30, index=1, level=2),
            _unit("wasp", x=-100, y=-30, index=2, level=2),
        ],
    ),
    {
        "must_address_threats": ["enemy_air_pressure"],
        "expected_influence_findings": ["anti_air_gap"],
        "recommended_response_types": ["add_anti_air"],
    },
    "Enemy has 3 wasps, player has no anti-air",
)

# 2. Anti-chaff gap
save(
    "case_002_chaff_flood",
    _state(
        my_units=[_unit("marksmen", x=0, y=-200), _unit("marksmen", x=100, y=-200, index=1)],
        enemy_units=[
            _unit("crawler", x=-80, y=-30),
            _unit("crawler", x=0, y=-30, index=1),
            _unit("crawler", x=80, y=-30, index=2),
            _unit("crawler", x=-40, y=-20, index=3),
            _unit("fang", x=40, y=-20, index=4),
        ],
    ),
    {
        "must_address_threats": ["enemy_chaff_overload"],
        "expected_influence_findings": ["anti_chaff_gap"],
        "recommended_response_types": ["add_anti_chaff"],
    },
    "Enemy floods with crawlers and fangs",
)

# 3. Anti-heavy gap
save(
    "case_003_heavy_frontline",
    _state(
        my_units=[_unit("crawler", x=0, y=-100), _unit("fang", x=-100, y=-100, index=1)],
        enemy_units=[
            _unit("fortress", x=0, y=-30),
            _unit("rhino", x=-100, y=-30, index=1),
            _unit("sabertooth", x=100, y=-30, index=2),
        ],
    ),
    {
        "must_address_threats": ["enemy_frontline_wall"],
        "expected_influence_findings": ["anti_heavy_gap"],
        "recommended_response_types": ["add_single_target"],
    },
    "Enemy has heavy frontline wall",
)

# 4. Artillery pressure
save(
    "case_004_artillery_backline",
    _state(
        my_units=[_unit("marksmen", x=0, y=-250), _unit("arclight", x=50, y=-200, index=1)],
        enemy_units=[
            _unit("sledgehammer", x=0, y=-80, level=2),
            _unit("stormcaller", x=-80, y=-80, index=1, level=2),
        ],
    ),
    {
        "must_address_threats": ["enemy_artillery_pressure"],
        "expected_influence_findings": ["artillery_danger"],
        "recommended_response_types": ["spread_backline", "flank_attack"],
    },
    "Enemy artillery overlaps backline",
)

# 5. Flank opportunity
save(
    "case_005_flank_opportunity",
    _state(
        my_units=[
            _unit("marksmen", x=-200, y=-150),
            _unit("marksmen", x=-100, y=-150, index=1),
            _unit("arclight", x=-150, y=-100, index=2),
        ],
        enemy_units=[
            _unit("fortress", x=100, y=-30),
            _unit("rhino", x=150, y=-30, index=1),
        ],
    ),
    {
        "must_address_threats": [],
        "expected_influence_findings": ["flank_opportunity"],
        "recommended_response_types": ["flank_pressure"],
    },
    "Enemy concentrated right, left flank open",
)

# 6. Tower pressure
save(
    "case_006_tower_pressure",
    _state(
        my_units=[_unit("crawler", x=0, y=-200)],
        enemy_units=[
            _unit("sledgehammer", x=0, y=-80, level=2),
            _unit("marksmen", x=50, y=-80, index=1, level=2),
        ],
        constructions=[
            ConstructionView(
                type=ConstructionType.COMMAND_TOWER, role=ConstructionRole.COMMAND,
                position=Position(x=0, y=-150), position_label="center_mid",
            ),
        ],
    ),
    {
        "must_address_threats": [],
        "expected_influence_findings": ["tower_pressure"],
        "recommended_response_types": ["protect_tower"],
    },
    "Enemy pressure overlaps tower zone",
)

# 7. Overreaction to weak air
save(
    "case_007_weak_air_no_overreact",
    _state(
        my_units=[
            _unit("marksmen", x=0, y=-150),
            _unit("arclight", x=50, y=-150, index=1),
            _unit("crawler", x=-50, y=-100, index=2),
        ],
        enemy_units=[
            _unit("wasp", x=200, y=-30),
            _unit("fortress", x=0, y=-30, index=1),
        ],
    ),
    {
        "must_address_threats": [],
        "forbidden_high_severity_findings": ["anti_air_gap"],
        "expected_influence_findings": [],
    },
    "Single wasp - should not trigger high-severity anti-air",
)

# 8. Safe scaling
save(
    "case_008_safe_scaling",
    _state(
        my_units=[
            _unit("marksmen", x=0, y=-200),
            _unit("arclight", x=-80, y=-150, index=1),
            _unit("crawler", x=0, y=-100, index=2),
            _unit("crawler", x=80, y=-100, index=3),
        ],
        enemy_units=[
            _unit("crawler", x=0, y=-30),
            _unit("crawler", x=80, y=-30, index=1),
        ],
        supply=800,
    ),
    {
        "must_address_threats": [],
        "expected_influence_findings": [],
        "forbidden_high_severity_findings": [],
    },
    "Balanced position, safe to scale economy",
)

# 9. Clumped placement
save(
    "case_009_clumped_units",
    _state(
        my_units=[
            _unit("marksmen", x=0, y=-200),
            _unit("marksmen", x=10, y=-195, index=1),
            _unit("marksmen", x=-10, y=-205, index=2),
            _unit("arclight", x=5, y=-190, index=3),
        ],
        enemy_units=[_unit("sledgehammer", x=0, y=-50, level=2)],
    ),
    {
        "must_address_threats": ["positioning_clump_risk"],
        "expected_influence_findings": ["artillery_danger"],
        "recommended_response_types": ["spread_backline"],
    },
    "All units clumped in center back - vulnerable to AoE",
)

# 10. No threat / economy
save(
    "case_010_economy_round",
    _state(
        my_units=[_unit("crawler", x=0, y=-100), _unit("arclight", x=80, y=-150, index=1)],
        enemy_units=[_unit("crawler", x=0, y=-30)],
        supply=400,
        round_num=2,
    ),
    {
        "must_address_threats": [],
        "expected_influence_findings": [],
        "forbidden_high_severity_findings": ["anti_air_gap", "anti_heavy_gap", "anti_chaff_gap"],
    },
    "Early game, no major threat - focus on economy",
)

print("Created 10 eval cases in eval_cases/")
