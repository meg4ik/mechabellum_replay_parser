"""Tests for knowledge package: parser and retriever."""

from pathlib import Path

import pytest

from mechabellum_replay_parser.coach.schemas import (
    PlayerRoundView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    UnitView,
)
from mechabellum_replay_parser.knowledge.parser import (
    _parse_markdown,
    parse_knowledge_file,
)
from mechabellum_replay_parser.knowledge.retriever import KnowledgeRetriever
from mechabellum_replay_parser.knowledge.schemas import KnowledgeChunk

# ── Minimal markdown fixture ──────────────────────────────────────────────────

_MINIMAL_MD = """\
## 1. What Mechabellum is

Mechabellum is a tactical auto-battler. Deployment decisions are the real gameplay.

### 3.1 Targeting

Units generally target the closest valid target. Chaff placement matters.

### 3.2 Chaff waves

Good chaff is not only front row. Chaff should arrive in waves for maximum effect.

### 6.5 Legal movement / repositioning constraint

Do not recommend moving or repositioning existing units unless a legal mechanism exists.

### 7.1 Arclight

Role: cheap/medium-range ground chaff clear. Excellent into Crawlers and Fangs.

Good into: Crawlers, Fangs.

Counters: Marksman, Phoenix if exposed.

### 7.2 Crawler

Role: cheapest high-speed melee chaff; one of the most important units in the game.

Good into: Marksmen, Phoenix when they lack chaff clear.

### 7.4 If enemy has air

Use Mustang, Marksman with Aerial Specialization, Farseer, Typhoon, Fortress AA.

### 3.12 Buildings, towers, and destruction consequences

Buildings are destructible. Core buildings apply tower debuff when destroyed.

### 8.1 Arclight + Marksman + Stormcaller standard

Arclights clear ground chaff. Marksmen kill high-value units. Stormcallers punish clumps.

## 14. Source notes for future refresh

Check wiki.mbxmas.com for updates. This section is not useful for LLM reasoning.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse(md: str = _MINIMAL_MD) -> list[KnowledgeChunk]:
    return _parse_markdown(md, source="test.md")


def _make_state(
    my_units: list[str] | None = None, enemy_units: list[str] | None = None
) -> StateView:
    my = [UnitView(name=n, index=i) for i, n in enumerate(my_units or [])]
    enemy = [UnitView(name=n, index=i) for i, n in enumerate(enemy_units or [])]
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=300,
        my_state=PlayerRoundView(name="Me", army_value=500, units=my),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=600, units=enemy)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _no_features(threats: list[ThreatSignal] | None = None) -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )


# ── Parser: chunk creation ────────────────────────────────────────────────────


def test_parse_returns_chunk_list():
    chunks = _parse()
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, KnowledgeChunk) for c in chunks)


def test_source_notes_section_skipped():
    chunks = _parse()
    assert not any("source note" in c.title.lower() for c in chunks)


def test_base_rules_chunk_exists():
    chunks = _parse()
    assert any(c.topic == "base_rules" for c in chunks)


def test_positioning_chunk_from_targeting():
    chunks = _parse()
    targeting = next((c for c in chunks if "targeting" in c.title.lower()), None)
    assert targeting is not None
    assert targeting.topic == "positioning"


def test_chaff_chunk_topic():
    chunks = _parse()
    chaff = next((c for c in chunks if "chaff wave" in c.title.lower()), None)
    assert chaff is not None
    assert chaff.topic == "chaff"


def test_deployment_rules_chunk():
    chunks = _parse()
    dep = next((c for c in chunks if "legal movement" in c.title.lower()), None)
    assert dep is not None
    assert dep.topic == "deployment_rules"


def test_towers_chunk():
    chunks = _parse()
    tower = next((c for c in chunks if "buildings, tower" in c.title.lower()), None)
    assert tower is not None
    assert tower.topic == "towers"


def test_unit_counter_chunk_for_arclight():
    chunks = _parse()
    arclight = next(
        (c for c in chunks if "arclight" in c.title.lower() and "7.1" in c.title), None
    )
    assert arclight is not None
    assert arclight.topic == "unit_counter"
    assert "arclight" in arclight.unit_names


def test_unit_counter_chunk_for_crawler():
    chunks = _parse()
    crawler = next(
        (c for c in chunks if "crawler" in c.title.lower() and "7.2" in c.title), None
    )
    assert crawler is not None
    assert "crawler" in crawler.unit_names


def test_unit_counter_topic_from_if_enemy_has():
    chunks = _parse()
    air = next((c for c in chunks if "if enemy has air" in c.title.lower()), None)
    assert air is not None
    assert air.topic == "unit_counter"


def test_composition_archetype_chunk():
    chunks = _parse()
    comp = next((c for c in chunks if "arclight + marksman" in c.title.lower()), None)
    assert comp is not None
    assert comp.topic == "unit_counter"


# ── Parser: priority and tags ─────────────────────────────────────────────────


def test_what_mechabellum_high_priority():
    chunks = _parse()
    br = next((c for c in chunks if "what mechabellum" in c.title.lower()), None)
    assert br is not None
    assert br.priority >= 2


def test_legal_movement_high_priority():
    chunks = _parse()
    dep = next((c for c in chunks if "legal movement" in c.title.lower()), None)
    assert dep is not None
    assert dep.priority >= 2


def test_towers_chunk_priority():
    chunks = _parse()
    tower = next((c for c in chunks if "buildings, tower" in c.title.lower()), None)
    assert tower is not None
    assert tower.priority >= 1


def test_topic_always_in_tags():
    chunks = _parse()
    for c in chunks:
        assert c.topic in c.tags


def test_unit_name_in_tags_for_unit_chunk():
    chunks = _parse()
    arclight = next((c for c in chunks if "arclight" in c.unit_names), None)
    assert arclight is not None
    assert "arclight" in arclight.tags


# ── Parser: IDs and content ───────────────────────────────────────────────────


def test_chunk_ids_are_slugs():
    for c in _parse():
        assert c.id
        assert " " not in c.id
        assert c.id == c.id.lower()


def test_chunk_ids_unique():
    chunks = _parse()
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_content_nonempty():
    for c in _parse():
        assert c.content.strip()


def test_parse_from_file(tmp_path):
    f = tmp_path / "test_knowledge.md"
    f.write_text(_MINIMAL_MD, encoding="utf-8")
    chunks = parse_knowledge_file(f)
    assert len(chunks) > 0


def test_parse_source_from_filename(tmp_path):
    f = tmp_path / "game_knowledge.md"
    f.write_text(_MINIMAL_MD, encoding="utf-8")
    chunks = parse_knowledge_file(f)
    assert all(c.source == "game_knowledge.md" for c in chunks)


def test_parse_custom_patch_version(tmp_path):
    f = tmp_path / "knowledge.md"
    f.write_text(_MINIMAL_MD, encoding="utf-8")
    chunks = parse_knowledge_file(f, patch_version="1.11")
    assert all(c.patch_version == "1.11" for c in chunks)


# ── Retriever: basic behaviour ────────────────────────────────────────────────


def test_retriever_returns_list_of_strings():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features())
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)


def test_retriever_empty_chunks():
    r = KnowledgeRetriever([])
    result = r.retrieve(_make_state(), _no_features())
    assert result == []


def test_retriever_always_includes_base_rules():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features())
    combined = "\n".join(result)
    assert "mechabellum" in combined.lower()


def test_retriever_always_includes_deployment_rules():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features())
    combined = "\n".join(result)
    assert "legal movement" in combined.lower() or "repositioning" in combined.lower()


def test_retriever_always_includes_towers_chunk():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features())
    combined = "\n".join(result)
    assert "tower" in combined.lower()


def test_retriever_respects_max_chunks():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features(), max_chunks=3)
    assert len(result) <= 3


def test_retriever_no_duplicate_chunks():
    r = KnowledgeRetriever(_parse())
    result = r.retrieve(_make_state(), _no_features())
    assert len(result) == len(set(result))


# ── Retriever: scoring ────────────────────────────────────────────────────────


def test_retriever_scores_enemy_unit_names():
    r = KnowledgeRetriever(_parse())
    state = _make_state(enemy_units=["arclight"])
    result = r.retrieve(state, _no_features(), max_chunks=5)
    combined = "\n".join(result)
    assert "arclight" in combined.lower()


def test_retriever_scores_my_unit_names():
    r = KnowledgeRetriever(_parse())
    state = _make_state(my_units=["crawler"])
    result = r.retrieve(state, _no_features(), max_chunks=5)
    combined = "\n".join(result)
    assert "crawler" in combined.lower()


def test_retriever_scores_threat_tags_air():
    r = KnowledgeRetriever(_parse())
    threats = [
        ThreatSignal(
            key="enemy_air_pressure",
            severity=0.9,
            source_units=["phoenix"],
            explanation="Enemy has air",
            my_answer="none",
        )
    ]
    result = r.retrieve(_make_state(), _no_features(threats=threats), max_chunks=6)
    combined = "\n".join(result)
    assert "air" in combined.lower() or "phoenix" in combined.lower()


def test_retriever_scores_source_unit_in_threats():
    r = KnowledgeRetriever(_parse())
    threats = [
        ThreatSignal(
            key="enemy_air_pressure",
            severity=0.8,
            source_units=["arclight"],
            explanation="Arclight threat",
            my_answer="none",
        )
    ]
    result = r.retrieve(_make_state(), _no_features(threats=threats), max_chunks=6)
    combined = "\n".join(result)
    assert "arclight" in combined.lower()


# ── Integration with real game_knowledge.md ───────────────────────────────────


def _find_real_knowledge() -> Path | None:
    candidate = Path(__file__).parent.parent / "game_knowledge.md"
    return candidate if candidate.exists() else None


def test_parse_real_game_knowledge():
    kf = _find_real_knowledge()
    if kf is None:
        pytest.skip("game_knowledge.md not found")
    chunks = parse_knowledge_file(kf)
    assert len(chunks) >= 30


def test_real_knowledge_has_unit_chunks():
    kf = _find_real_knowledge()
    if kf is None:
        pytest.skip("game_knowledge.md not found")
    chunks = parse_knowledge_file(kf)
    unit_chunks = [c for c in chunks if c.unit_names]
    assert len(unit_chunks) >= 15


def test_real_knowledge_always_include_chunk_count():
    kf = _find_real_knowledge()
    if kf is None:
        pytest.skip("game_knowledge.md not found")
    chunks = parse_knowledge_file(kf)
    always = [
        c
        for c in chunks
        if c.topic in {"base_rules", "deployment_rules", "towers"} and c.priority >= 1
    ]
    assert len(always) >= 3


def test_real_knowledge_retriever_with_air_threat():
    kf = _find_real_knowledge()
    if kf is None:
        pytest.skip("game_knowledge.md not found")
    chunks = parse_knowledge_file(kf)
    r = KnowledgeRetriever(chunks)
    state = _make_state(my_units=["marksman"], enemy_units=["wasp", "phoenix"])
    threats = [
        ThreatSignal(
            key="enemy_air_pressure",
            severity=0.9,
            source_units=["wasp", "phoenix"],
            explanation="Enemy air",
            my_answer="none",
        )
    ]
    result = r.retrieve(state, _no_features(threats=threats), max_chunks=8)
    assert len(result) > 0
    combined = "\n".join(result)
    assert (
        "air" in combined.lower()
        or "wasp" in combined.lower()
        or "phoenix" in combined.lower()
    )


def test_real_knowledge_retriever_returns_formatted_sections():
    kf = _find_real_knowledge()
    if kf is None:
        pytest.skip("game_knowledge.md not found")
    chunks = parse_knowledge_file(kf)
    r = KnowledgeRetriever(chunks)
    result = r.retrieve(_make_state(), _no_features(), max_chunks=5)
    for section in result:
        assert section.startswith("## ")
