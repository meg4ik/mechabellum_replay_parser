def test_metadata_version(parsed_replay):
    assert parsed_replay["metadata"]["version"] == "1.0.0"


def test_metadata_match_mode(parsed_replay):
    assert parsed_replay["metadata"]["match_mode"] == "VS_2_2"


def test_teams_structure(parsed_replay):
    teams = parsed_replay["teams"]
    assert isinstance(teams, list)
    assert len(teams) == 2
    assert "Player1" in teams[0]
    assert "Player2" in teams[1]


def test_last_round(parsed_replay):
    assert parsed_replay["last_round"] == 1


def test_rounds_count(parsed_replay):
    assert len(parsed_replay["rounds"]) == 1


def test_round_shape(parsed_replay):
    r = parsed_replay["rounds"][0]
    assert r["round"] == 1
    assert "fight_result" in r
    assert "players" in r


def test_player_fields_present(parsed_replay):
    player = parsed_replay["rounds"][0]["players"]["Player1"]
    for field in (
        "hp",
        "supply",
        "army_value",
        "fight_outcome",
        "officers",
        "commander_skills",
        "units",
        "active_techs",
        "contraptions",
        "constructions",
        "shop",
        "actions",
    ):
        assert field in player, f"missing player field: {field}"


def test_player_hp(parsed_replay):
    assert parsed_replay["rounds"][0]["players"]["Player1"]["hp"] == 3


def test_player_fight_outcome(parsed_replay):
    assert parsed_replay["rounds"][0]["players"]["Player1"]["fight_outcome"] == "win"


def test_player_army_value(parsed_replay):
    # One crawler with sell_supply=60
    assert parsed_replay["rounds"][0]["players"]["Player1"]["army_value"] == 60


def test_unit_shape(parsed_replay):
    units = parsed_replay["rounds"][0]["players"]["Player1"]["units"]
    assert len(units) == 1
    u = units[0]
    assert u["name"] == "crawler"
    assert u["unit_id"] == 10
    assert u["index"] == 0
    assert u["level"] == 1
    assert u["exp"] == 0
    assert u["rounds_survived"] == 0
    assert u["position"] == {"x": -40, "y": -80}
    assert u["equipment"] is None
    assert u["sell_supply"] == 60
    assert u["rotate"] is False


def test_construction_shape(parsed_replay):
    constructions = parsed_replay["rounds"][0]["players"]["Player1"]["constructions"]
    assert len(constructions) == 1
    c = constructions[0]
    assert c["type"] == "Defensive Wall"
    assert c["construction_id"] == 1
    assert c["index"] == 0
    assert c["position"] == {"x": 100, "y": -270}


def test_shop_unlocked(parsed_replay):
    shop = parsed_replay["rounds"][0]["players"]["Player1"]["shop"]
    assert "crawler" in shop["unlocked"]


def test_shop_locked(parsed_replay):
    shop = parsed_replay["rounds"][0]["players"]["Player1"]["shop"]
    assert "arclight" in shop["locked"]


def test_shop_buys_remaining(parsed_replay):
    shop = parsed_replay["rounds"][0]["players"]["Player1"]["shop"]
    assert shop["buys_remaining"] == 4


def test_shop_unlocks_remaining(parsed_replay):
    shop = parsed_replay["rounds"][0]["players"]["Player1"]["shop"]
    assert shop["unlocks_remaining"] == 1


def test_fight_result_player1(parsed_replay):
    fr = parsed_replay["rounds"][0]["fight_result"]
    assert fr is not None
    assert fr["Player1"]["crystals_destroyed"] == 0
    assert fr["Player1"]["units_survived"] == 4
    assert fr["Player1"]["score"] == 120


def test_fight_result_player2(parsed_replay):
    fr = parsed_replay["rounds"][0]["fight_result"]
    assert fr["Player2"]["crystals_destroyed"] == 1
    assert fr["Player2"]["units_survived"] == 0


def test_player2_empty_units(parsed_replay):
    units = parsed_replay["rounds"][0]["players"]["Player2"]["units"]
    assert units == []


def test_actions_list(parsed_replay):
    actions = parsed_replay["rounds"][0]["players"]["Player1"]["actions"]
    assert isinstance(actions, list)
