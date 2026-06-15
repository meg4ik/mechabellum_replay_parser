"""Tag-based knowledge retriever (v1 — no embeddings)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .schemas import KnowledgeChunk

if TYPE_CHECKING:
    from ..coach.schemas import StateView, TacticalFeatures

# These topics always contribute their high-priority chunks to every query.
_ALWAYS_INCLUDE_TOPICS: frozenset[str] = frozenset({"base_rules", "deployment_rules", "towers"})

# Map known threat keys to additional scoring tags.
_THREAT_KEY_TAGS: dict[str, list[str]] = {
    "enemy_air_pressure": ["air", "unit_counter"],
    "enemy_chaff_flood": ["chaff", "unit_counter"],
    "enemy_heavy_frontline": ["frontline", "unit_counter"],
    "enemy_artillery": ["artillery", "unit_counter"],
}


class KnowledgeRetriever:
    """Returns relevant knowledge chunks as formatted strings.

    Always-include: chunks whose topic is in _ALWAYS_INCLUDE_TOPICS *and*
    whose priority >= 1.  Remaining budget is filled by scoring other chunks
    on tag overlap and unit-name overlap with the current game state.
    """

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks

    def retrieve(
        self,
        state: StateView,
        features: TacticalFeatures,
        max_chunks: int = 10,
    ) -> list[str]:
        if not self._chunks:
            return []

        always = [
            c for c in self._chunks
            if c.topic in _ALWAYS_INCLUDE_TOPICS and c.priority >= 2
        ]
        always_ids = {c.id for c in always}

        query_tags, query_units = self._build_query(state, features)

        scored: list[tuple[int, KnowledgeChunk]] = []
        for chunk in self._chunks:
            if chunk.id in always_ids:
                continue
            score = self._score(chunk, query_tags, query_units)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: -x[0])
        budget = max(0, max_chunks - len(always))
        selected = always + [c for _, c in scored[:budget]]

        return [f"## {c.title}\n\n{c.content}" for c in selected]

    # ── private helpers ──────────────────────────────────────────────────────

    def _build_query(
        self,
        state: StateView,
        features: TacticalFeatures,
    ) -> tuple[set[str], set[str]]:
        tags: set[str] = set()
        units: set[str] = set()

        for unit in state.my_state.units:
            units.add(unit.name.lower())
        for es in state.enemy_states:
            for unit in es.units:
                units.add(unit.name.lower())
        for c in state.my_state.constructions:
            if c.type:
                units.add(c.type.lower())

        for threat in features.threats:
            tags.add(threat.key)
            for u in threat.source_units:
                units.add(u.lower())
            for extra_tag in _THREAT_KEY_TAGS.get(threat.key, []):
                tags.add(extra_tag)

        for weakness in features.my_weaknesses:
            w = weakness.lower()
            if "air" in w:
                tags.add("air")
            if "chaff" in w:
                tags.add("chaff")
            if "artillery" in w or "missile" in w:
                tags.add("artillery")
            if "giant" in w or "heavy" in w or "frontline" in w:
                tags.add("frontline")

        return tags, units

    def _score(
        self,
        chunk: KnowledgeChunk,
        query_tags: set[str],
        query_units: set[str],
    ) -> int:
        chunk_tags = set(chunk.tags)
        chunk_units = {u.lower() for u in chunk.unit_names}

        score = chunk.priority  # priority bonus
        score += len(query_tags & chunk_tags) * 2
        score += len(query_units & chunk_units) * 3
        return score
