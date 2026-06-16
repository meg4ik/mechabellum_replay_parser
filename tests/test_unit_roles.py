"""Tests for unit_roles module (Phase 3)."""

from mechabellum_replay_parser.coach.unit_roles import get_tags, get_unit_data, has_tag


# ── get_tags ──────────────────────────────────────────────────────────────────


def test_crawler_has_chaff_tag():
    assert has_tag("crawler", "chaff")


def test_phoenix_has_air_tag():
    assert has_tag("phoenix", "air")


def test_arclight_has_anti_air_tag():
    assert has_tag("arclight", "anti_air")


def test_arclight_has_anti_chaff_tag():
    assert has_tag("arclight", "anti_chaff")


def test_stormcaller_multi_role():
    tags = get_tags("stormcaller")
    assert "artillery" in tags
    assert "anti_chaff" in tags
    assert "anti_air" in tags


def test_fortress_has_heavy_frontline():
    assert has_tag("fortress", "heavy_frontline")


def test_fortress_has_tank():
    assert has_tag("fortress", "tank")


def test_overlord_has_air_and_scaling():
    tags = get_tags("overlord")
    assert "air" in tags
    assert "scaling" in tags


def test_warfactory_has_scaling():
    assert has_tag("warfactory", "scaling")


def test_marksmen_has_single_target_and_backline_carry():
    tags = get_tags("marksmen")
    assert "single_target" in tags
    assert "backline_carry" in tags


# ── has_tag negative ──────────────────────────────────────────────────────────


def test_fortress_not_air():
    assert not has_tag("fortress", "air")


def test_crawler_not_anti_air():
    assert not has_tag("crawler", "anti_air")


def test_rhino_not_chaff():
    assert not has_tag("rhino", "chaff")


# ── unknown unit ──────────────────────────────────────────────────────────────


def test_unknown_unit_returns_empty_tags():
    assert get_tags("nonexistent_unit") == []


def test_unknown_unit_has_tag_false():
    assert not has_tag("nonexistent_unit", "air")


# ── get_unit_data ─────────────────────────────────────────────────────────────


def test_get_unit_data_returns_dict_with_tags():
    data = get_unit_data("crawler")
    assert isinstance(data, dict)
    assert "tags" in data


def test_get_unit_data_has_value():
    data = get_unit_data("fortress")
    assert data.get("value") == 400


def test_get_unit_data_case_insensitive():
    assert get_unit_data("CRAWLER") == get_unit_data("crawler")


def test_get_unit_data_unknown_returns_empty():
    assert get_unit_data("does_not_exist") == {}
