"""Parse game_knowledge.md into KnowledgeChunk records."""

from __future__ import annotations

import re
from pathlib import Path

from .schemas import KnowledgeChunk

# Matches H2 (##) and H3 (###) headings only — H4 (####) stay inside parent chunks.
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)

# Strips leading section numbers: "7.1 Arclight" → "Arclight"
_NUMBER_PREFIX_RE = re.compile(r"^\d+\.?\d*\.?\d*\s+")

_MIN_CONTENT_LENGTH = 20

_ALL_UNITS: frozenset[str] = frozenset(
    {
        "arclight",
        "crawler",
        "fang",
        "hound",
        "marksman",
        "void eye",
        "vortex",
        "fire badger",
        "hacker",
        "mustang",
        "phantom ray",
        "phoenix",
        "rhino",
        "sabertooth",
        "sledgehammer",
        "steel ball",
        "stormcaller",
        "tarantula",
        "wasp",
        "farseer",
        "scorpion",
        "typhoon",
        "wraith",
        "fortress",
        "melting point",
        "raiden",
        "sandworm",
        "vulcan",
        "overlord",
        "abyss",
        "death knell",
        "mountain",
        "war factory",
    }
)

# (substring of lowercased title, topic) — first match wins; None = skip chunk
_TOPIC_RULES: list[tuple[str, str | None]] = [
    ("source note", None),
    ("known patch", "patch_notes"),
    ("final instruction", "base_rules"),
    ("unit technology scope", "unit_tech"),
    ("unit technology catalog", "unit_tech"),
    ("100-cost unit", "unit_tech"),
    ("200-cost unit", "unit_tech"),
    ("300-cost unit", "unit_tech"),
    ("400/500", "unit_tech"),
    ("800-cost", "unit_tech"),
    ("chaff wave", "chaff"),
    ("missile interception", "artillery"),
    ("legal movement", "deployment_rules"),
    ("unit reinforcement", "economy"),
    ("experience and level", "scaling"),
    ("late game", "scaling"),
    ("mobile beacon", "positioning"),
    ("unit orientation", "positioning"),
    ("flank", "positioning"),
    ("targeting", "positioning"),
    ("equipment", "cards"),
    ("commander", "cards"),
    ("captain", "cards"),
    ("enemy can break", "tower_destruction"),
    ("i can break enemy", "tower_destruction"),
    ("tower-pressure", "tower_destruction"),
    ("tower-defense", "tower_destruction"),
    ("core building", "towers"),
    ("command center abilit", "buildings"),
    ("research center abilit", "buildings"),
    ("building categor", "buildings"),
    ("defensive construction", "buildings"),
    ("tower", "towers"),
    ("building", "buildings"),
    ("supply income", "supply"),
    ("carryover rule", "supply"),
    ("income rule", "supply"),
    ("regular card economy", "economy"),
    ("budget validation", "economy"),
    ("break-even", "economy"),
    ("specialist economy", "specialists"),
    ("starting specialist", "specialists"),
    ("unit purchase cost", "economy"),
    ("unlock cost", "economy"),
    ("economy", "economy"),
    (" + ", "unit_counter"),  # composition names: "Arclight + Marksman + ..."
    ("composition", "unit_counter"),
    ("anti-giant", "unit_counter"),
    ("air punish", "unit_counter"),
    ("shield standard", "unit_counter"),
    ("i am losing", "common_mistakes"),
    ("enemy has too much", "unit_counter"),
    ("enemy stormcaller", "unit_counter"),
    ("enemy hacker", "unit_counter"),
    ("enemy flanks", "common_mistakes"),
    ("i have supply", "common_mistakes"),
    ("counter matrix", "unit_counter"),
    ("counter logic", "unit_counter"),
    ("unit knowledge", "unit_counter"),
    ("composition archetype", "unit_counter"),
    ("if enemy has", "unit_counter"),
    ("decision heuristic", "common_mistakes"),
    ("strategic dos", "common_mistakes"),
    ("board-state analysis", "base_rules"),
    ("what mechabellum", "base_rules"),
    ("vocabulary", "base_rules"),
    ("strategic role", "base_rules"),
    ("basic terms", "base_rules"),
    ("buffs", "base_rules"),
    ("core mechanic", "base_rules"),
    ("game plan", "base_rules"),
    ("early game", "base_rules"),
    ("mid game", "base_rules"),
    ("high-level game", "base_rules"),
]

# (substring in lowercased title, priority value)
_PRIORITY_RULES: list[tuple[str, int]] = [
    ("what mechabellum", 2),
    ("vocabulary and strategic", 1),
    ("final instruction", 2),
    ("legal movement", 2),
    ("unit technology scope", 2),
    ("board-state analysis", 2),
    ("buildings, tower", 2),  # towers topic must be always-include
    ("compact counter matrix", 1),
    ("strategic dos and don", 1),
    ("tower-pressure", 1),
    ("core mechanic", 1),
    ("game plan", 1),
    ("basic terms", 1),
    ("strategic role", 1),
    ("vocabulary and strategic", 1),
]

# Content keywords that add extra tags (first 1000 chars checked, each tag added at most once)
_CONTENT_TAG_RULES: list[tuple[str, str]] = [
    ("anti-air", "air"),
    ("anti-aircraft", "air"),
    ("aerial", "air"),
    ("chaff clear", "chaff"),
    ("tower pressure", "tower_destruction"),
    ("tower debuff", "tower_destruction"),
    ("break tower", "tower_destruction"),
    ("missile interception", "artillery"),
    ("scaling", "scaling"),
]


def parse_knowledge_file(
    path: Path,
    source: str | None = None,
    patch_version: str | None = None,
) -> list[KnowledgeChunk]:
    text = path.read_text(encoding="utf-8")
    return _parse_markdown(
        text, source=source or path.name, patch_version=patch_version
    )


def _parse_markdown(
    text: str,
    source: str,
    patch_version: str | None = None,
) -> list[KnowledgeChunk]:
    matches = list(_HEADING_RE.finditer(text))
    chunks: list[KnowledgeChunk] = []

    for i, m in enumerate(matches):
        title = m.group(2).strip()
        content_start = m.end() + 1  # skip the \n after heading
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()

        chunk = _make_chunk(title, content, source, patch_version)
        if chunk is not None:
            chunks.append(chunk)

    return chunks


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")[:64]


_SKIP = "__skip__"  # sentinel returned when a chunk should be omitted


def _determine_topic(title_lower: str) -> str:
    """Return topic string, _SKIP to omit the chunk, or '' to trigger unit-name fallback."""
    for pattern, topic in _TOPIC_RULES:
        if pattern in title_lower:
            return topic if topic is not None else _SKIP
    return ""  # no explicit rule — caller falls back to unit-name / base_rules


def _determine_priority(title_lower: str) -> int:
    for pattern, priority in _PRIORITY_RULES:
        if pattern in title_lower:
            return priority
    return 0


def _extract_unit_names(title: str) -> list[str]:
    bare = _NUMBER_PREFIX_RE.sub("", title).strip().lower()
    if bare in _ALL_UNITS:
        return [bare]
    # Broader check: any known unit names appearing as substrings in the title
    title_lower = title.lower()
    return [u for u in _ALL_UNITS if u in title_lower]


def _extract_content_tags(content: str, seen: set[str]) -> list[str]:
    snippet = content.lower()[:1000]
    extra: list[str] = []
    for keyword, tag in _CONTENT_TAG_RULES:
        if tag not in seen and keyword in snippet:
            extra.append(tag)
            seen.add(tag)
    return extra


def _make_chunk(
    title: str,
    content: str,
    source: str,
    patch_version: str | None,
) -> KnowledgeChunk | None:
    if len(content) < _MIN_CONTENT_LENGTH:
        return None

    title_lower = title.lower()
    raw_topic = _determine_topic(title_lower)

    if raw_topic is _SKIP:
        return None  # section explicitly excluded

    if raw_topic == "":
        # No explicit rule matched — fall back to unit-name then base_rules
        unit_names = _extract_unit_names(title)
        topic = "unit_counter" if unit_names else "base_rules"
    else:
        topic = raw_topic
        unit_names = _extract_unit_names(title)

    priority = _determine_priority(title_lower)

    seen_tags: set[str] = {topic}
    tags: list[str] = [topic]
    for u in unit_names:
        if u not in seen_tags:
            tags.append(u)
            seen_tags.add(u)
    tags.extend(_extract_content_tags(content, seen_tags))

    return KnowledgeChunk(
        id=_slugify(title),
        source=source,
        patch_version=patch_version,
        title=title,
        content=content,
        tags=tags,
        unit_names=unit_names,
        topic=topic,
        priority=priority,
    )
