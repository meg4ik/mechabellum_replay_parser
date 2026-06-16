from mechabellum_replay_parser.llm import parse_placement


def _wrap(json_str: str) -> str:
    return f"PLACEMENT:\n```json\n{json_str}\n```"


def test_valid_single_entry():
    text = _wrap('[{"unit": "crawler", "x": 0, "y": -80, "action": "keep"}]')
    result = parse_placement(text)
    assert result == [{"unit": "crawler", "x": 0, "y": -80, "action": "keep"}]


def test_multiple_entries():
    text = _wrap(
        '[{"unit": "crawler", "x": -40, "y": -80, "action": "keep"},'
        ' {"unit": "arclight", "x": 20, "y": -160, "action": "new"}]'
    )
    result = parse_placement(text)
    assert len(result) == 2
    assert result[1]["unit"] == "arclight"
    assert result[1]["action"] == "new"


def test_clamp_x_too_large():
    text = _wrap('[{"unit": "arclight", "x": 999, "y": -100, "action": "move"}]')
    result = parse_placement(text)
    assert result[0]["x"] == 285


def test_clamp_x_too_small():
    text = _wrap('[{"unit": "arclight", "x": -999, "y": -100, "action": "move"}]')
    result = parse_placement(text)
    assert result[0]["x"] == -285


def test_clamp_y_above_front_line():
    text = _wrap('[{"unit": "arclight", "x": 0, "y": -10, "action": "new"}]')
    result = parse_placement(text)
    assert result[0]["y"] == -45


def test_clamp_y_beyond_back_line():
    text = _wrap('[{"unit": "arclight", "x": 0, "y": -999, "action": "new"}]')
    result = parse_placement(text)
    assert result[0]["y"] == -295


def test_coordinates_at_exact_bounds_not_clamped():
    text = _wrap('[{"unit": "fang", "x": -285, "y": -295, "action": "keep"}]')
    result = parse_placement(text)
    assert result[0]["x"] == -285
    assert result[0]["y"] == -295


def test_default_action_is_keep():
    text = _wrap('[{"unit": "fang", "x": 0, "y": -100}]')
    result = parse_placement(text)
    assert result[0]["action"] == "keep"


def test_no_placement_block_returns_none():
    assert parse_placement("some text without a placement block") is None


def test_empty_array_returns_none():
    assert parse_placement(_wrap("[]")) is None


def test_invalid_json_returns_none():
    assert parse_placement("PLACEMENT:\n```json\nnot_json\n```") is None


def test_missing_unit_field_skips_entry():
    text = _wrap('[{"x": 0, "y": -80, "action": "keep"}]')
    assert parse_placement(text) is None


def test_mixed_valid_and_invalid_entries():
    text = _wrap(
        '[{"x": 0, "y": -80}, {"unit": "crawler", "x": 0, "y": -80, "action": "keep"}]'
    )
    result = parse_placement(text)
    assert result is not None
    assert len(result) == 1
    assert result[0]["unit"] == "crawler"
