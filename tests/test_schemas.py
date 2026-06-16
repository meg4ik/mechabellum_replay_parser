from mechabellum_replay_parser.schemas import (
    Construction,
    ParsedReplay,
    PlacementEntry,
    Position,
    Shop,
    Unit,
)


def test_position_model():
    p = Position(x=10, y=-80)
    assert p.x == 10
    assert p.y == -80


def test_unit_model():
    u = Unit(
        name="crawler",
        unit_id=10,
        index=0,
        level=1,
        exp=0,
        rounds_survived=0,
        position={"x": -40, "y": -80},
        equipment=None,
        sell_supply=60,
        rotate=False,
    )
    assert u.name == "crawler"
    assert u.position.x == -40
    assert u.position.y == -80


def test_unit_null_position():
    u = Unit(
        name="crawler",
        unit_id=10,
        index=0,
        level=1,
        exp=0,
        rounds_survived=0,
        position=None,
        equipment=None,
        sell_supply=60,
        rotate=False,
    )
    assert u.position is None


def test_construction_model():
    c = Construction(
        type="Defensive Wall",
        construction_id=1,
        index=0,
        position={"x": 100, "y": -270},
    )
    assert c.type == "Defensive Wall"
    assert c.position.x == 100


def test_shop_model_full():
    s = Shop(
        unlocked=["crawler"], locked=["arclight"], buys_remaining=4, unlocks_remaining=1
    )
    assert s.buys_remaining == 4
    assert "crawler" in s.unlocked


def test_shop_model_empty_dict():
    s = Shop.model_validate({})
    assert s.unlocked == []
    assert s.buys_remaining is None


def test_placement_entry_model():
    e = PlacementEntry(unit="crawler", x=0, y=-80, action="keep")
    assert e.action == "keep"
    assert e.x == 0


def test_parsed_replay_validates(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    assert replay.last_round == 1
    assert replay.metadata.version == "1.0.0"
    assert replay.metadata.match_mode == "VS_2_2"


def test_parsed_replay_teams(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    assert "Player1" in replay.teams[0]
    assert "Player2" in replay.teams[1]


def test_parsed_replay_unit_deserialized(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    unit = replay.rounds[0].players["Player1"].units[0]
    assert unit.name == "crawler"
    assert unit.position.x == -40


def test_parsed_replay_construction_deserialized(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    c = replay.rounds[0].players["Player1"].constructions[0]
    assert c.type == "Defensive Wall"
    assert c.position.y == -270


def test_parsed_replay_shop_deserialized(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    shop = replay.rounds[0].players["Player1"].shop
    assert shop.buys_remaining == 4
    assert "crawler" in shop.unlocked


def test_parsed_replay_fight_result(parsed_replay):
    replay = ParsedReplay.model_validate(parsed_replay)
    fr = replay.rounds[0].fight_result
    assert fr["Player1"].crystals_destroyed == 0
    assert fr["Player2"].crystals_destroyed == 1
