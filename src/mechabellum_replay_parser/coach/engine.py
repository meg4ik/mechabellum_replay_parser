from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..knowledge.parser import parse_knowledge_file
from ..knowledge.retriever import KnowledgeRetriever
from ..llm.client import LLMProvider
from ..llm.providers.openai_provider import OpenAIProvider
from .coordinates import CoordinateFrame
from .feature_extractor import FeatureExtractor
from .influence_analyzer import InfluenceAnalyzer
from .influence_map import InfluenceMapBuilder
from .influence_schemas import InfluenceAnalysisSummary
from .judge import Judge, _make_fallback_judge_output
from .legal_actions import LegalActionGenerator
from .tactical_bundles import TacticalBundleGenerator
from .plan_scorer import PlanScorer
from .placement_resolver import PlacementResolver
from .planner import Planner, _make_fallback_plan
from .recommendation_builder import RecommendationBuilder
from .unit_stats import UnitStatsResolver
from .schemas import (
    CandidatePlan,
    CoachRecommendation,
    JudgeOutput,
    PlanValidationResult,
    StateView,
)
from .state_view import StateViewBuilder
from .validator import PlanValidator

_log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_DEFAULT_KNOWLEDGE_FILE = (
    Path(__file__).parent.parent.parent.parent / "game_knowledge.md"
)
_DEBUG_DIR = Path(".debug")


@dataclass
class CoachAnalysis:
    """Full pipeline result — recommendation plus all intermediate data for persistence."""

    recommendation: CoachRecommendation
    state_view: StateView | None = None
    validated_plans: list[tuple[CandidatePlan, PlanValidationResult]] = field(
        default_factory=list
    )
    judge_output: JudgeOutput | None = None
    model_name: str | None = None
    pipeline_run_id: str | None = None
    stage_timings: dict[str, int] = field(default_factory=dict)
    influence_summary: InfluenceAnalysisSummary | None = None
    score_breakdowns: list = field(default_factory=list)


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are a Mechabellum AI coach. ({name} prompt not found)"


def _load_retriever() -> KnowledgeRetriever:
    kf = Path(os.getenv("MECHABELLUM_KNOWLEDGE_FILE", str(_DEFAULT_KNOWLEDGE_FILE)))
    chunks = parse_knowledge_file(kf) if kf.exists() else []
    return KnowledgeRetriever(chunks)


def _default_provider() -> LLMProvider:
    return OpenAIProvider()


def _is_debug() -> bool:
    return os.getenv("DEBUG", "").lower() in ("1", "true", "yes")


def _write_debug(name: str, data) -> None:
    if not _is_debug():
        return
    try:
        _DEBUG_DIR.mkdir(exist_ok=True)
        path = _DEBUG_DIR / name
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
    except Exception as exc:
        _log.debug("Debug artifact write failed for %s: %s", name, exc)


class CoachEngine:
    """Orchestrates the full coaching pipeline.

    StateViewBuilder → FeatureExtractor → LegalActionGenerator
    → KnowledgeRetriever → Planner (LLM) → PlanValidator
    → Judge (LLM) → RecommendationBuilder
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        p = provider or _default_provider()
        self._state_view_builder = StateViewBuilder()
        self._feature_extractor = FeatureExtractor()
        self._legal_action_generator = LegalActionGenerator()
        self._bundle_generator = TacticalBundleGenerator()
        self._unit_stats_resolver = UnitStatsResolver()
        self._influence_map_builder = InfluenceMapBuilder(self._unit_stats_resolver)
        self._influence_analyzer = InfluenceAnalyzer()
        self._plan_scorer = PlanScorer()
        self._plan_validator = PlanValidator()
        self._placement_resolver = PlacementResolver()
        self._planner = Planner(p, _load_prompt("planner_v1"))
        self._judge = Judge(p, _load_prompt("judge_v1"))
        self._recommendation_builder = RecommendationBuilder()
        self._retriever = _load_retriever()

    async def analyze_replay(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
    ) -> CoachRecommendation:
        return (
            await self.analyze_replay_detailed(parsed, supply, player_name)
        ).recommendation

    async def analyze_replay_detailed(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
        rec_id: str | None = None,
    ) -> CoachAnalysis:
        pipeline_run_id = uuid.uuid4().hex[:8]
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        timings: dict[str, int] = {}

        def _ms(t0: float) -> int:
            return int((time.monotonic() - t0) * 1000)

        _ctx = f"run_id={pipeline_run_id}"
        if rec_id:
            _ctx += f" rec_id={rec_id}"

        _t = time.monotonic()
        state = self._state_view_builder.build(parsed, supply, player_name)
        timings["state_view_ms"] = _ms(_t)
        _log.info(
            "%s stage=state_view_built round=%s player=%s supply=%s elapsed_ms=%d",
            _ctx,
            state.round,
            player_name,
            supply,
            timings["state_view_ms"],
        )
        _write_debug("latest_state_view.json", state.model_dump())
        _write_debug(
            "latest_constructions.json",
            [c.model_dump() for c in state.my_state.constructions],
        )

        _t = time.monotonic()
        features = self._feature_extractor.extract(state)
        timings["features_ms"] = _ms(_t)
        _log.info(
            "%s stage=features_extracted threats=%d tempo=%s posture=%s elapsed_ms=%d",
            _ctx,
            len(features.threats),
            features.tempo_state,
            features.board_posture,
            timings["features_ms"],
        )
        _write_debug("latest_features.json", features.model_dump())

        _t = time.monotonic()
        legal_actions, action_groups = self._legal_action_generator.generate(
            state, features
        )
        timings["legal_actions_ms"] = _ms(_t)
        _log.info(
            "%s stage=legal_actions_generated count=%d groups=%d elapsed_ms=%d",
            _ctx,
            len(legal_actions),
            len(action_groups),
            timings["legal_actions_ms"],
        )
        _write_debug(
            "latest_legal_actions.json", [a.model_dump() for a in legal_actions]
        )

        _t = time.monotonic()
        bundles = self._bundle_generator.generate(state, features, legal_actions)
        timings["tactical_bundles_ms"] = _ms(_t)
        _log.info(
            "%s stage=bundles_generated count=%d elapsed_ms=%d",
            _ctx,
            len(bundles),
            timings["tactical_bundles_ms"],
        )
        _write_debug("latest_bundles.json", [b.model_dump() for b in bundles])

        _t = time.monotonic()
        knowledge_chunks = self._retriever.retrieve(state, features)
        timings["knowledge_retrieval_ms"] = _ms(_t)
        _log.info(
            "%s stage=knowledge_retrieved chunks=%d elapsed_ms=%d",
            _ctx,
            len(knowledge_chunks),
            timings["knowledge_retrieval_ms"],
        )

        # Coordinate frame — always compute for debug visibility
        frame = CoordinateFrame.from_units_and_constructions(
            state.my_state.units, state.my_state.constructions
        )
        opp_frame = frame.opponent_frame() if state.round >= 2 else None
        _write_debug("latest_coordinate_frame.json", frame.model_dump())

        # Influence map — non-fatal, pipeline continues if it fails
        influence_summary: InfluenceAnalysisSummary | None = None
        try:
            _t = time.monotonic()
            influence_result = self._influence_map_builder.build(state, frame)
            timings["influence_map_ms"] = _ms(_t)
            _log.info(
                "%s stage=influence_map_built zones=%d elapsed_ms=%d",
                _ctx,
                len(influence_result.zones),
                timings["influence_map_ms"],
            )
            _write_debug(
                "latest_influence_map_summary.json",
                [z.model_dump() for z in influence_result.zones],
            )

            _t = time.monotonic()
            influence_summary = self._influence_analyzer.analyze(
                state,
                features,
                influence_result,
            )
            timings["influence_analyzer_ms"] = _ms(_t)
            _log.info(
                "%s stage=influence_analyzed findings=%d elapsed_ms=%d",
                _ctx,
                len(influence_summary.tactical_findings),
                timings["influence_analyzer_ms"],
            )
            _write_debug(
                "latest_influence_findings.json",
                influence_summary.model_dump(mode="json"),
            )

            if _is_debug():
                try:
                    from ..debug.influence_debug import write_influence_csv

                    write_influence_csv(influence_result, _DEBUG_DIR)
                except Exception:
                    pass
        except Exception as exc:
            _log.warning(
                "%s stage=influence_failed error=%s — continuing without influence",
                _ctx,
                exc,
            )

        planner_call_id = uuid.uuid4().hex[:8]
        _log.info(
            "%s stage=planner_started planner_call_id=%s timeout_s=%s model=%s",
            _ctx,
            planner_call_id,
            timeout,
            model_name,
        )
        _t = time.monotonic()
        try:
            plans = await asyncio.wait_for(
                self._planner.generate_plans(
                    state,
                    features,
                    action_groups,
                    knowledge_chunks,
                    bundles,
                    legal_actions,
                    influence=influence_summary,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "%s stage=planner_timeout planner_call_id=%s seconds=%s — using fallback plan",
                _ctx,
                planner_call_id,
                timeout,
            )
            plans = [_make_fallback_plan(state)]
        timings["planner_llm_ms"] = _ms(_t)
        _log.info(
            "%s stage=planner_completed planner_call_id=%s plans=%d elapsed_ms=%d",
            _ctx,
            planner_call_id,
            len(plans),
            timings["planner_llm_ms"],
        )
        _write_debug("latest_planner_response.json", [p.model_dump() for p in plans])

        _t = time.monotonic()
        validated_plans = [
            (
                plan,
                self._plan_validator.validate_placement(
                    plan.placement, state, legal_actions
                ),
            )
            for plan in plans
        ]
        timings["validator_ms"] = _ms(_t)
        valid_count = sum(1 for _, r in validated_plans if r.is_valid)
        _log.info(
            "%s stage=validation_completed total=%d valid=%d elapsed_ms=%d",
            _ctx,
            len(validated_plans),
            valid_count,
            timings["validator_ms"],
        )
        _write_debug(
            "latest_validation.json",
            [
                {
                    "plan_id": p.id,
                    "is_valid": r.is_valid,
                    "issues": [i.model_dump() for i in r.issues],
                }
                for p, r in validated_plans
            ],
        )

        _t = time.monotonic()
        score_breakdowns = self._plan_scorer.score_all(
            validated_plans,
            features,
            state,
            influence=influence_summary,
        )
        timings["plan_scorer_ms"] = _ms(_t)
        _log.info(
            "%s stage=plans_scored count=%d elapsed_ms=%d",
            _ctx,
            len(score_breakdowns),
            timings["plan_scorer_ms"],
        )
        _write_debug(
            "latest_plan_scores.json",
            [s.model_dump() for s in score_breakdowns],
        )
        if _is_debug() and influence_summary:
            try:
                from ..debug.influence_debug import write_influence_plan_deltas

                write_influence_plan_deltas(
                    [s.model_dump() for s in score_breakdowns],
                    _DEBUG_DIR,
                )
            except Exception:
                pass

        judge_call_id = uuid.uuid4().hex[:8]
        _log.info(
            "%s stage=judge_started judge_call_id=%s model=%s",
            _ctx,
            judge_call_id,
            model_name,
        )
        _t = time.monotonic()
        try:
            judge_output = await asyncio.wait_for(
                self._judge.select_plan(
                    state,
                    features,
                    validated_plans,
                    knowledge_chunks,
                    score_breakdowns,
                    influence=influence_summary,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "%s stage=judge_timeout judge_call_id=%s seconds=%s — picking highest-confidence valid plan",
                _ctx,
                judge_call_id,
                timeout,
            )
            judge_output = _make_fallback_judge_output(
                validated_plans, score_breakdowns
            )
        timings["judge_llm_ms"] = _ms(_t)
        _log.info(
            "%s stage=judge_completed judge_call_id=%s best_plan_id=%s confidence=%s elapsed_ms=%d",
            _ctx,
            judge_call_id,
            judge_output.best_plan_id,
            judge_output.confidence,
            timings["judge_llm_ms"],
        )
        _write_debug("latest_judge_response.json", judge_output.model_dump())

        selected_plan = next(
            (p for p, _ in validated_plans if p.id == judge_output.best_plan_id),
            validated_plans[0][0] if validated_plans else None,
        )
        _t = time.monotonic()
        resolved_placements = []
        if selected_plan and selected_plan.placement_intents:
            resolved_placements = self._placement_resolver.resolve(
                selected_plan.placement_intents,
                frame,
                state.my_state.units,
                opponent_frame=opp_frame,
            )
        timings["placement_resolver_ms"] = _ms(_t)
        _log.info(
            "%s stage=placement_resolved count=%d elapsed_ms=%d",
            _ctx,
            len(resolved_placements),
            timings["placement_resolver_ms"],
        )
        _write_debug(
            "latest_resolved_placement.json",
            [r.model_dump() for r in resolved_placements],
        )

        recommendation = self._recommendation_builder.build(
            judge_output,
            validated_plans,
            features,
            state,
            resolved_placements=resolved_placements or None,
        )
        total_ms = sum(timings.values())
        _log.info(
            "%s stage=recommendation_ready summary=%r placement_items=%d total_ms=%d",
            _ctx,
            recommendation.summary,
            len(recommendation.placement or []),
            total_ms,
        )
        _write_debug(
            "latest_recommendation.json",
            {
                "summary": recommendation.summary,
                "coach_text": recommendation.coach_text,
                "placement": recommendation.placement,
            },
        )
        _write_debug("latest_timings.json", timings)

        if _is_debug():
            from ..debug.report_builder import save_report as _save_report

            try:
                _save_report(_DEBUG_DIR)
            except Exception as exc:
                _log.debug("Debug report generation failed: %s", exc)
            if influence_summary:
                try:
                    from ..debug.influence_debug import build_influence_report

                    report_md = build_influence_report(
                        influence_summary,
                        [s.model_dump() for s in score_breakdowns],
                    )
                    (_DEBUG_DIR / "latest_influence_report.md").write_text(
                        f"# Influence Analysis Report\n\n{report_md}",
                        encoding="utf-8",
                    )
                except Exception as exc:
                    _log.debug("Influence report generation failed: %s", exc)

        _log.info(
            "%s pipeline_complete round=%s total_ms=%d model=%s",
            _ctx,
            state.round,
            total_ms,
            model_name,
        )

        return CoachAnalysis(
            recommendation=recommendation,
            state_view=state,
            validated_plans=validated_plans,
            judge_output=judge_output,
            model_name=model_name,
            pipeline_run_id=pipeline_run_id,
            stage_timings=timings,
            influence_summary=influence_summary,
            score_breakdowns=score_breakdowns,
        )

    def build_state_view(self, parsed: dict, supply: int | None, player_name: str):
        """Expose StateViewBuilder for external callers."""
        return self._state_view_builder.build(parsed, supply, player_name)
