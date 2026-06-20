# Mechabellum Replay Analyzer — Technical Documentation

## Overview

Real-time AI tactical advisor for Mechabellum. Monitors the Steam replay folder, parses `.grbr` replay files as they appear, asks the player for their current supply, runs a multi-stage LLM coaching pipeline, and streams tactical recommendations to a persistent native Tkinter window.

**Deployment split:** backend (parser, watcher, FastAPI, CoachEngine, DB) runs in Docker; the Tkinter supply dialog and board visualization run natively on the host and communicate with the Docker backend over HTTP/WebSocket.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | ≥ 3.13 |
| Package manager / venv | [uv](https://github.com/astral-sh/uv) | any |
| Build backend | hatchling | any |
| Filesystem monitoring | watchdog | ≥ 6.0 |
| LLM client | openai (Python SDK) | ≥ 1.0 |
| API framework | FastAPI + uvicorn | ≥ 0.115 |
| WebSocket transport | websockets | ≥ 12.0 |
| HTTP client | httpx2 | ≥ 0.28 |
| Config / secrets | python-dotenv | ≥ 1.0 |
| Data validation | pydantic v2 | ≥ 2.0 |
| Database ORM | SQLAlchemy 2 async | ≥ 2.0 |
| DB driver | asyncpg (prod) / aiosqlite (tests) | ≥ 0.29 / 0.20 |
| DB migrations | Alembic | ≥ 1.13 |
| GUI | tkinter (stdlib, host only) | — |
| Replay parsing | xml.etree.ElementTree (stdlib) | — |
| CLI table output | prettytable | ≥ 3.14 |
| Influence map computation | numpy | ≥ 2.0 |
| Linter / formatter | ruff | dev |
| Test runner | pytest + anyio | dev |
| Version bumping | bumpver | dev |

---

## Project Structure

```
mechabellum_replay_parser/
│
├── src/mechabellum_replay_parser/
│   ├── __init__.py              # Lookup tables + legacy parser API
│   ├── schemas.py               # Top-level Pydantic models (replay domain: Position, Unit, Shop, etc.)
│   ├── cli.py                   # CLI entry point (argparse)
│   ├── watcher.py               # Filesystem monitor + pipeline orchestration
│   ├── transformer.py           # .grbr XML → Python dict
│   ├── display.py               # Legacy tkinter board (CLI path only)
│   │
│   ├── api/
│   │   ├── app.py               # FastAPI app + lifespan (watcher, DB, broker)
│   │   ├── routes_health.py     # GET /health
│   │   ├── routes_ui.py         # POST /ui/supply-response
│   │   ├── routes_events.py     # GET /events/ws (WebSocket event stream)
│   │   └── routes_feedback.py   # POST /feedback
│   │
│   ├── coach/
│   │   ├── engine.py            # CoachEngine: full pipeline orchestrator
│   │   ├── schemas.py           # Pydantic models (StateView, CandidatePlan, PlacementIntent, TacticalBundle, …)
│   │   ├── state_view.py        # StateViewBuilder: parsed dict → StateView
│   │   ├── feature_extractor.py # FeatureExtractor: StateView → TacticalFeatures
│   │   ├── legal_actions.py     # LegalActionGenerator: what the player can do
│   │   ├── tactical_bundles.py  # TacticalBundleGenerator: groups legal actions into themed bundles
│   │   ├── coordinates.py       # CoordinateFrame: lane/depth semantic coordinate system
│   │   ├── constructions.py     # Construction ID→type mapping + enrichment
│   │   ├── unit_roles.py        # Unit role data (anti-air, anti-chaff, scaling, etc.)
│   │   ├── unit_stats.py        # UnitStatsResolver: unit+level+techs → combat stats (HP, DPS, range)
│   │   ├── influence_schemas.py # Pydantic schemas for influence map outputs (JSON-safe, no NumPy)
│   │   ├── influence_map.py     # InfluenceMapBuilder: 12-channel NumPy influence computation
│   │   ├── influence_analyzer.py # InfluenceAnalyzer: numeric fields → tactical findings
│   │   ├── plan_scorer.py       # PlanScorer: deterministic scoring + influence-aware components
│   │   ├── validator.py         # PlanValidator: legality + bounds check
│   │   ├── planner.py           # Planner: LLM → list[CandidatePlan] (receives influence findings)
│   │   ├── judge.py             # Judge: LLM selects best plan (receives influence scores)
│   │   ├── placement_resolver.py # PlacementResolver: PlacementIntent → ResolvedPlacement (x,y)
│   │   └── recommendation_builder.py  # Builds final CoachRecommendation
│   │
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM: Match, Round, Recommendation, …
│   │   ├── repositories.py      # RecommendationRepository, FeedbackRepository
│   │   ├── service.py           # PersistenceService facade (no-op if DEBUG_NO_DB)
│   │   └── session.py           # async engine + session factory
│   │
│   ├── debug/
│   │   ├── report_builder.py    # Builds Markdown debug report from .debug/ artifacts
│   │   └── influence_debug.py   # Influence-specific debug: CSV export, plan deltas, Markdown report
│   │
│   ├── eval/
│   │   ├── cases.py             # EvalCase + EvalExpected models, case loading
│   │   ├── rubric.py            # EvalRubric: scoring rubric for eval cases
│   │   ├── runner.py            # EvalRunner: runs pipeline stages on eval cases
│   │   └── report.py            # Saves eval report JSON to .debug/
│   │
│   ├── events/
│   │   ├── in_memory.py         # InMemoryBroker (asyncio-based pub/sub)
│   │   └── schemas.py           # UIEvent, SupplyRequestPayload, RecommendationReadyPayload
│   │
│   ├── knowledge/
│   │   ├── parser.py            # Parses game_knowledge.md → list[KnowledgeChunk]
│   │   ├── schemas.py           # KnowledgeChunk Pydantic model
│   │   └── retriever.py         # KnowledgeRetriever: tag-based RAG
│   │
│   ├── learning/
│   │   ├── outcomes.py          # OutcomeSummary: compute outcomes from successive StateView snapshots
│   │   └── dataset_export.py    # JSONL dataset export for recommendation quality training
│   │
│   ├── llm/
│   │   ├── client.py            # LLMProvider ABC
│   │   ├── parse.py             # Placement block parser (extracted from legacy llm.py)
│   │   └── providers/
│   │       ├── openai_provider.py  # OpenAI async JSON completion
│   │       └── local_provider.py   # Fake provider for tests
│   │
│   ├── native_ui/
│   │   ├── client.py            # CoreAPIClient: HTTP + WebSocket to Docker API
│   │   ├── display.py           # CoachWindow: persistent Tkinter window (4 states)
│   │   └── main.py              # Entry point: starts CoachWindow + asyncio thread
│   │
│   ├── prompts/
│   │   ├── planner_v1.md        # System prompt for Planner LLM call
│   │   └── judge_v1.md          # System prompt for Judge LLM call
│   │
│   └── data/
│       ├── unit_data.json           # Static unit cost/tag data
│       ├── construction_data.json   # Construction type/role mapping data
│       ├── unit_combat_data.json    # Combat stats: HP, DPS, range, speed, squad_size, target profiles
│       ├── tech_modifiers.json      # Tech effect multipliers (range, DPS, HP)
│       └── unit_matchup_modifiers.json # Per-unit effectiveness vs target categories
│
├── alembic/
│   ├── env.py                   # Async Alembic env
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   └── 002_add_influence_fields.py  # Adds influence JSON columns
│   └── script.py.mako
│
├── tests/
│   ├── conftest.py              # shared parsed_replay fixture
│   ├── fixtures/                # JSON snapshots for reproducible tests
│   │   ├── parsed_round_early.json
│   │   ├── parsed_round_air_threat.json
│   │   ├── parsed_round_construction.json
│   │   ├── llm_planner_valid.json
│   │   ├── llm_planner_invalid.json
│   │   └── llm_judge_valid.json
│   ├── test_transformer.py
│   ├── test_state_view.py
│   ├── test_feature_extractor.py
│   ├── test_legal_actions.py
│   ├── test_tactical_bundles.py
│   ├── test_constructions.py
│   ├── test_coordinates.py
│   ├── test_unit_roles.py
│   ├── test_plan_scorer.py
│   ├── test_validator.py
│   ├── test_planner.py
│   ├── test_judge.py
│   ├── test_placement_resolver.py
│   ├── test_recommendation_builder.py
│   ├── test_parse_placement.py
│   ├── test_llm_pipeline.py     # integration tests using fixtures
│   ├── test_api.py
│   ├── test_api_events.py       # event schema + /feedback endpoint
│   ├── test_broker.py
│   ├── test_db.py
│   ├── test_db_feedback.py
│   ├── test_debug_report_builder.py
│   ├── test_native_ui.py
│   ├── test_knowledge.py
│   ├── test_schemas.py
│   ├── test_unit_drops.py
│   ├── test_unit_stats.py
│   ├── test_influence_schemas.py
│   ├── test_influence_map.py
│   ├── test_influence_analyzer.py
│   ├── test_influence_plan_scorer.py
│   ├── test_influence_llm_contract.py
│   ├── test_influence_debug.py
│   ├── test_eval_cases.py
│   ├── test_eval_rubric.py
│   ├── test_eval_runner.py
│   ├── test_eval_influence.py
│   ├── test_learning_outcomes.py
│   ├── test_learning_export.py
│   ├── test_learning_influence_export.py
│   └── test_db_influence.py
│
├── eval_cases/                  # 10 eval cases for influence + pipeline testing
│   ├── case_001_air_threat/
│   ├── case_002_chaff_flood/
│   ├── case_003_heavy_frontline/
│   ├── case_004_artillery_backline/
│   ├── case_005_flank_opportunity/
│   ├── case_006_tower_pressure/
│   ├── case_007_weak_air_no_overreact/
│   ├── case_008_safe_scaling/
│   ├── case_009_clumped_units/
│   └── case_010_economy_round/
├── scripts/
│   ├── stats.py                 # Utility stats script
│   └── gen_eval_cases.py        # Generates eval case fixtures
│
├── game_knowledge.md            # Tactical knowledge base (~2100 lines, 95 chunks)
├── Dockerfile                   # Python 3.13-slim + uv, runs uvicorn
├── docker-compose.yml           # core-api + postgres (pgvector/pgvector:pg16)
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── TECHNICAL.md                 # ← this file
├── USAGE.md
├── PROJECT_OVERVIEW.md
├── 2v2_unknowns.md              # Notes on 2v2 mode parsing edge cases
├── .env                         # Secret/config values (not committed)
├── .env.example
├── .justfile                    # just task runner recipes
└── .python-version
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `PLAYER_NAME` | Yes | — | Your in-game name (exact match) |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model for Planner and Judge |
| `DATABASE_URL` | No | `postgresql+asyncpg://mechabellum:mechabellum@localhost:5432/mechabellum` | Async DB URL |
| `REPLAY_DIR` | No | Steam default path | Path to replay folder (inside Docker: `/data/replays`) |
| `DEBUG` | No | `false` | If `true`/`1`/`yes`: skip LLM + write debug artifacts to `.debug/` |
| `DEBUG_NO_DB` | No | `false` | If `true`/`1`/`yes`: disable DB persistence (no-op PersistenceService) |
| `LLM_TIMEOUT_SECONDS` | No | `60` | Per-call timeout for Planner and Judge LLM calls |
| `SUPPLY_TIMEOUT` | No | `300` | Seconds to wait for native UI supply input before proceeding |
| `REPLAY_AFTER_PROCESS` | No | `delete` | What to do with `.grbr` after processing: `delete`, `archive`, or `keep` |
| `CORE_API_URL` | No | `http://localhost:8000` | Native UI → Docker API base URL |
| `CORE_WS_URL` | No | `ws://localhost:8000/events/ws` | Native UI WebSocket URL |
| `MECHABELLUM_KNOWLEDGE_FILE` | No | `game_knowledge.md` (repo root) | Path to knowledge base |
| `MECHABELLUM_REPLAY_DIR` | Docker only | — | Host path to replay folder (docker-compose volume source) |

---

## Full Pipeline (current)

```
[Steam] saves .grbr → Replay folder
    │
    ▼
[watchdog] FileCreatedEvent → process_replay(path)   [watcher.py]
    │  log: replay_detected
    │
    ▼
[watcher] wait for file to stabilize (3× same size, 0.5s)
    │  log: replay_stabilized
    │
    ▼
[transformer] extract_xml() → ET.fromstring() → replay_to_dict()
    │  log: replay_parsed   debug: .debug/latest_parsed.json
    │
    ▼
[broker] publish supply_request event → WebSocket to native UI
    │  log: supply_requested
    │
    ▼
[native_ui] CoachWindow shows supply input dialog (Tkinter, host)
    │  user enters supply → POST /ui/supply-response → broker resolves Future
    │  log: supply_received
    │
    ▼
[CoachEngine.analyze_replay_detailed()]             [coach/engine.py]
    │
    ├─ StateViewBuilder.build()          → StateView
    │    log: state_view_built    debug: latest_state_view.json, latest_constructions.json
    │
    ├─ FeatureExtractor.extract()        → TacticalFeatures
    │    log: features_extracted  debug: latest_features.json
    │
    ├─ LegalActionGenerator.generate()   → legal_actions, action_groups
    │    log: legal_actions_generated  debug: latest_legal_actions.json
    │
    ├─ TacticalBundleGenerator.generate()→ list[TacticalBundle]
    │    log: bundles_generated   debug: latest_bundles.json
    │
    ├─ CoordinateFrame.from_units_and_constructions() → frame
    │    debug: latest_coordinate_frame.json
    │
    ├─ InfluenceMapBuilder.build()       → InfluenceMapResult (12-channel NumPy arrays)
    │    log: influence_map_built  debug: latest_influence_map_summary.json
    │    non-fatal: pipeline continues if influence fails
    │
    ├─ InfluenceAnalyzer.analyze()       → InfluenceAnalysisSummary
    │    log: influence_analyzed   debug: latest_influence_findings.json
    │    6 finding types: anti_air_gap, anti_chaff_gap, anti_heavy_gap,
    │                     artillery_danger, flank_opportunity, tower_pressure
    │
    ├─ KnowledgeRetriever.retrieve()     → relevant knowledge chunks (RAG)
    │    log: knowledge_retrieved
    │
    ├─ Planner.generate_plans()  [LLM call, timeout: LLM_TIMEOUT_SECONDS]
    │    receives: influence_analysis (compact findings, not raw arrays)
    │    → list[CandidatePlan]
    │    log: planner_started / planner_completed  debug: latest_planner_response.json
    │    fallback: keep-all plan on timeout / error
    │
    ├─ PlanValidator.validate_placement() (per plan)
    │    log: validation_completed  debug: latest_validation.json
    │
    ├─ PlanScorer.score_all()            → list[PlanScoreBreakdown]
    │    log: plans_scored        debug: latest_plan_scores.json
    │    includes influence_improvement, anti_air/chaff/heavy scores when available
    │    debug: latest_influence_plan_deltas.json (if influence present)
    │
    ├─ Judge.select_plan()       [LLM call, timeout: LLM_TIMEOUT_SECONDS]
    │    receives: influence_analysis + influence-enhanced plan scores
    │    → JudgeOutput
    │    log: judge_started / judge_completed  debug: latest_judge_response.json
    │    fallback: highest-confidence valid plan on timeout / error
    │
    ├─ PlacementResolver.resolve()       → list[ResolvedPlacement]
    │    log: placement_resolved  debug: latest_resolved_placement.json
    │
    └─ RecommendationBuilder.build()     → CoachRecommendation
         log: recommendation_ready  debug: latest_recommendation.json, latest_timings.json
    │
    ▼
[debug/report_builder] (if DEBUG=true) saves latest_failure_report.md
    │
    ▼
[PersistenceService.save_match_analysis()]          [db/service.py]
    │  saves: Match, Round, Recommendation, CandidatePlanRow, LLMCall
    │  non-fatal on DB errors; no-op if DEBUG_NO_DB=true
    │
    ▼
[broker] publish recommendation_ready event → WebSocket to native UI
    │  log: ui_event_sent
    │
    ▼
[native_ui] CoachWindow shows result (summary, coach text, board canvas)
    │  user can click 👍 / 👎 → POST /feedback
    │  log: feedback_received
    │
    ▼
[PersistenceService.save_feedback()]
    │  saves: Feedback row   non-fatal on DB errors
    │
    ▼
[watcher] delete / archive / keep .grbr (per REPLAY_AFTER_PROCESS)
```

---

## CoachEngine Pipeline (detail)

### StateView

Compact game state object used by all downstream pipeline stages. Built by `StateViewBuilder` from the parsed replay dict.

Key fields: `match_mode`, `round`, `player_name`, `enemy_names`, `my_supply`, `my_state` (PlayerRoundView with units/shop/constructions), `enemy_states`, `recent_rounds`, `strategic_memory`.

### TacticalFeatures

Extracted signals from `StateView`. Generated by `FeatureExtractor`.

Key fields: `threats` (list of ThreatSignal with key/severity/source_units/my_answer), `my_weaknesses`, `enemy_weaknesses`, `tempo_state` (ahead/even/behind), `board_posture`, `tower_notes`, `likely_enemy_continuation`, `priority_questions`.

**Threat keys:** `enemy_air_pressure`, `enemy_chaff_flood`, `enemy_artillery`, `enemy_heavy_frontline`, `construction_lost`.

### LegalAction / ActionGroup

What the player is legally allowed to do this round. Generated by `LegalActionGenerator`.

Action types: `buy` (available units in shop), `upgrade` (units already on field), `tech` (researched techs), `unlock` (locked units needing unlock), `move` (repositioning).

Actions grouped by tactical theme (ActionGroup) for the Planner prompt.

### TacticalBundle

Groups of legal actions organized by tactical theme (e.g., anti-air, economy, flanking). Generated by `TacticalBundleGenerator` from the state, features, and legal actions.

Key fields: `id`, `theme` (TacticalTheme enum), `title`, `required_action_ids`, `optional_action_ids`, `estimated_cost`, `placement_intents`, `why_considered`, `risks`.

### CoordinateFrame

Semantic coordinate system mapping lanes (LEFT, LEFT_CENTER, CENTER, RIGHT_CENTER, RIGHT) and depths (FRONT, MID_FRONT, MID, MID_BACK, BACK) to raw game coordinates. Detects player side (NEGATIVE_Y / POSITIVE_Y) from existing unit positions. Used by `PlacementResolver` to convert `PlacementIntent` → absolute (x, y).

### PlacementIntent / ResolvedPlacement

**PlacementIntent** — LLM-generated placement in semantic terms: `unit`, `action` (KEEP/MOVE/NEW), `lane`, `depth`, `zone` (OWN/OPPONENT), `anchor`, `purpose`.

**ResolvedPlacement** — Concrete (x, y) coordinates resolved from intent by `PlacementResolver`, with collision avoidance.

### CandidatePlan

LLM Planner output: a proposed buy/placement strategy.

Key fields: `id`, `title`, `action_ids`, `total_cost`, `main_goal`, `why_it_works`, `risks`, `expected_enemy_response`, `placement` (list of dict for backward compat), `placement_intents` (list of PlacementIntent), `confidence`.

### PlanScoreBreakdown

Deterministic score computed by `PlanScorer` for each candidate plan.

Key fields: `plan_id`, `total_score`, `threat_coverage`, `supply_efficiency`, `tempo`, `scaling`, `positioning_safety`, `tower_protection`, `flexibility_next_round`, `overreaction_risk`, `legality_penalty`.

**Influence-aware fields** (populated when InfluenceAnalysisSummary is available): `influence_improvement`, `anti_air_improvement`, `anti_chaff_improvement`, `anti_heavy_improvement`, `artillery_risk_reduction`, `influence_explanation`.

### PlanValidationResult

Output of `PlanValidator.validate_placement()`. Checks coordinate bounds, unit legality, supply limits.

- `severity="error"` → `is_valid=False` (e.g., buying a locked unit, out-of-bounds coordinates)
- `severity="warning"` → plan stays valid (e.g., supply overspend approximation)

### JudgeOutput

LLM Judge output: selects the best CandidatePlan.

Key fields: `best_plan_id`, `confidence`, `main_reason`, `placement`, `watch_next_round`, `mistake_to_avoid`.

Fallback (`_make_fallback_judge_output`): picks the first valid plan (using PlanScoreBreakdown ranking) without LLM if Judge times out or fails.

### ConstructionView

Rich representation of in-game constructions (towers, walls, mines, etc.). Built by `constructions.py` from raw replay data with construction ID → type/role mapping.

Key fields: `type` (ConstructionType), `role` (ConstructionRole), `status` (ConstructionStatus), `position`, `position_label`.

---

## Influence Map Layer

Deterministic positional pressure analysis computed by Python code (not LLM). Adds numeric evidence about where enemy pressure is concentrated, where coverage gaps exist, and whether a plan closes a real tactical gap.

### UnitStatsResolver

Resolves `(unit_name, level, active_techs)` → `ResolvedUnitStats` with effective HP, DPS (ground/air), range, anti_chaff_score, anti_heavy_score. Uses `unit_combat_data.json` + `tech_modifiers.json` + `unit_matchup_modifiers.json`. Level scaling: `1.0 + 0.35 * (level - 1)`.

### InfluenceMapBuilder

Builds a 30×20 NumPy grid covering the full board. 12 channels: `{my,enemy}_{ground,air,anti_chaff,anti_heavy,artillery,durability}`. Each unit stamps influence via sigmoid range falloff: `influence = DPS / (1 + exp((distance - range) / softness))`. Zone aggregation produces 9 `ZoneInfluenceSummary` objects (3×3 grid: left/center/right × front/mid/back).

### InfluenceAnalyzer

Converts numeric influence data into compact `TacticalInfluenceFinding` objects that the LLM can reason about. Six V1 finding types:

| Finding | Condition | Response types |
|---|---|---|
| `anti_air_gap` | Enemy has air units, my anti-air coverage low | add_anti_air, shift_anti_air |
| `anti_chaff_gap` | Enemy chaff flood, my anti-chaff low | add_anti_chaff, upgrade_splash |
| `anti_heavy_gap` | Enemy heavy frontline, my anti-heavy low | add_single_target, unlock_anti_heavy |
| `artillery_danger` | Enemy pressure overlaps my backline/mid | spread_backline, flank_attack |
| `flank_opportunity` | Enemy pressure low on flank, opportunity high | flank_pressure, fast_chaff_flank |
| `tower_pressure` | Enemy pressure overlaps my construction zone | protect_tower, add_frontline |

Plus global assessment: `ground_balance`, `air_balance`, `frontline_balance`, `artillery_pressure`.

**LLM contract:** LLM receives only compact findings (key, severity, zone, evidence, recommended_response_types). Never raw NumPy arrays or heatmaps.

---

## Native UI Architecture

`CoachWindow` (Tkinter) runs on the main thread. An asyncio event loop runs in a daemon background thread.

```
Main thread          Background thread
─────────────        ──────────────────
CoachWindow          asyncio loop
  show_supply_prompt()    ← window.show_*(callback)   via root.after(0, ...)
  show_loading()
  show_result()
  [button click] ────────────────────→ asyncio.run_coroutine_threadsafe(coro, loop)
                         CoreAPIClient.post_supply_response()
                         CoreAPIClient.post_feedback()
```

**Window states:**
1. **idle** — "Ожидаю новую партию…"
2. **supply** — round number + supply entry + Подтвердить/Пропустить buttons
3. **loading** — animated 6-frame dot spinner (260ms)
4. **result** — summary (18pt bold) + scrollable coach text (13pt) + 840×460 board canvas + 👍/👎 feedback bar

---

## Database Schema (7 tables)

| Table | Purpose |
|---|---|
| `matches` | One row per processed `.grbr` file |
| `rounds` | Round number + player name per match |
| `recommendations` | Final CoachRecommendation + influence_summary_json + influence_findings_json |
| `candidate_plans` | All Planner candidate plans + plan_score_json + influence_delta_json |
| `llm_calls` | Latency + model + prompt version for each LLM call |
| `feedback` | User 👍/👎 per recommendation |
| `outcome_snapshots` | Post-round HP/outcome (for future outcome logging) |

**Migrations:** `alembic upgrade head`

**Test DB:** `sqlite+aiosqlite:///:memory:` (no Postgres needed for `pytest`)

---

## Eval Framework

Offline evaluation of the deterministic pipeline stages (feature extraction, legal actions, bundles, influence map, plan scoring) without LLM calls.

- `eval/cases.py` — `EvalCase` + `EvalExpected` (threats, response types, influence findings, critical zones, forbidden findings)
- `eval/rubric.py` — `EvalRubric` + `RubricScores`: 6 base dimensions + 3 influence dimensions (finding_accuracy, zone_accuracy, plan_improvement)
- `eval/runner.py` — `EvalRunner`: runs full deterministic pipeline including influence stages, produces `EvalResult`
- `eval/report.py` — saves eval results to `.debug/latest_eval_report.json`
- `eval_cases/` — 10 eval cases covering anti-air, chaff, heavy, artillery, flank, tower, overreaction, scaling, clumping, economy

---

## Learning / Outcome Tracking

- `learning/outcomes.py` — `OutcomeSummary`: computes HP delta, fight outcome, units survived from successive `StateView` snapshots
- `learning/dataset_export.py` — exports recommendation + outcome + influence data as JSONL. Each row includes `influence_summary`, `influence_findings`, `plan_influence_deltas`, `score_breakdowns` when available. Backward-compatible with older rows without influence.

---

## Structured Logging

All modules use `logging.getLogger(__name__)` with `stage=X key=value` structured format.

**Pipeline stages (in order):**

```
watcher_started          watcher.py
replay_detected          watcher.py
replay_stabilized_failed watcher.py       (if file didn't stabilize)
replay_stabilized        watcher.py
replay_parsed            watcher.py
supply_requested         watcher.py
supply_received          watcher.py
supply_timeout           watcher.py
state_view_built         coach/engine.py
features_extracted       coach/engine.py
legal_actions_generated  coach/engine.py
bundles_generated        coach/engine.py
influence_map_built      coach/engine.py
influence_analyzed       coach/engine.py
influence_failed         coach/engine.py       (non-fatal, pipeline continues)
knowledge_retrieved      coach/engine.py
planner_started          coach/engine.py
planner_completed        coach/engine.py
planner_timeout          coach/engine.py
validation_completed     coach/engine.py
plans_scored             coach/engine.py
judge_started            coach/engine.py
judge_completed          coach/engine.py
judge_timeout            coach/engine.py
placement_resolved       coach/engine.py
recommendation_ready     coach/engine.py
pipeline_complete        coach/engine.py
ui_event_sent            watcher.py
feedback_received        api/routes_feedback.py
```

---

## Debug Artifacts

When `DEBUG=true`, intermediate pipeline results are written to `.debug/`:

| File | Contents |
|---|---|
| `latest_parsed.json` | Full replay dict from `replay_to_dict()` |
| `latest_state_view.json` | StateView model dump |
| `latest_constructions.json` | Constructions from the current round |
| `latest_features.json` | TacticalFeatures model dump |
| `latest_legal_actions.json` | All legal actions list |
| `latest_bundles.json` | TacticalBundle list |
| `latest_coordinate_frame.json` | CoordinateFrame model dump |
| `latest_planner_response.json` | All CandidatePlans from Planner |
| `latest_plan_scores.json` | PlanScoreBreakdown per plan |
| `latest_validation.json` | Per-plan validation results |
| `latest_judge_response.json` | JudgeOutput |
| `latest_recommendation.json` | Final summary + coach_text + placement |
| `latest_resolved_placement.json` | ResolvedPlacement list (concrete x,y) |
| `latest_timings.json` | Per-stage timing in milliseconds |
| `latest_failure_report.md` | Human-readable Markdown debug report |
| `latest_influence_map_summary.json` | Zone influence summaries (9 zones × 11 metrics) |
| `latest_influence_findings.json` | Full InfluenceAnalysisSummary (findings, zones, global assessment) |
| `latest_influence_plan_deltas.json` | Per-plan influence improvement scores |
| `latest_influence_report.md` | Markdown influence analysis report |
| `latest_influence_my_ground.csv` | Raw influence grid: my ground DPS channel |
| `latest_influence_enemy_ground.csv` | Raw influence grid: enemy ground DPS channel |
| `latest_influence_my_air.csv` | Raw influence grid: my anti-air DPS channel |
| `latest_influence_enemy_air.csv` | Raw influence grid: enemy anti-air DPS channel |

---

## Coordinate System

```
x: -285 (left flank) ──────── 0 (center) ──────── +285 (right flank)

y: -45   ← front line (closest to enemy)    ← maps to TOP of canvas
y: -295  ← back line                        ← maps to BOTTOM of canvas

Positive-Y zone (second player slot in 2v2):
y: +45 front / +295 back — detected automatically
```

**Deployment zone bounds (validator):** x ∈ [-285, 285], y ∈ [-295, -45] or [45, 295]

**Semantic coordinates (CoordinateFrame):**
- Lanes: LEFT (-228), LEFT_CENTER (-114), CENTER (0), RIGHT_CENTER (+114), RIGHT (+228)
- Depths: FRONT, MID_FRONT, MID, MID_BACK, BACK — mapped to y ranges based on player side

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Returns `{"status": "ok"}` |
| GET | `/events/ws` | WebSocket stream of UIEvent JSON |
| POST | `/ui/supply-response` | Native UI sends supply after dialog |
| POST | `/feedback` | Native UI sends 👍/👎 after recommendation |

**Supply response body:** `{recommendation_id, supply, cancelled}`

**Feedback body:** `{recommendation_id, rating (1–5), label, comment, followed_plan}`

**Valid feedback labels:** `good`, `bad_illegal`, `bad_strategy`, `bad_positioning`, `bad_counter`, `too_expensive`, `unclear`

---

## Docker

```yaml
# docker-compose.yml services:
core-api:    # Python 3.13-slim + uv, runs uvicorn on :8000
postgres:    # pgvector/pgvector:pg16, DB: mechabellum
```

Volumes: replay dir (bind mount from host), `game_knowledge.md` (read-only), `.debug/` (bind mount).

**Build:** `docker compose build`
**Start:** `docker compose up -d`

---

## Error Handling Policy

The app must not crash on:
- Malformed replay → log + emit `error` UIEvent
- Missing player name → log + emit error
- LLM timeout → use fallback plan (Planner) or highest-confidence valid plan (Judge)
- Invalid LLM JSON → use fallback plan
- Validator rejecting all plans → fallback plan is always added
- DB temporarily unavailable → log warning, continue (non-fatal)
- Native UI disconnected → watcher continues; UI reconnects automatically

---

## Dev Commands

```bash
uv run pytest tests/             # run all 688 tests (41 test files)
uv run ruff check src/           # lint (must pass clean)
uv run ruff format src/          # auto-format
uv run mechabellum-replay-parser watch         # start watcher (CLI path)
uv run mech-native-ui                          # start native Tkinter UI
uv run uvicorn mechabellum_replay_parser.api.app:app --reload  # Docker API
uv run alembic upgrade head      # apply DB migrations
docker compose up -d             # start Docker stack (API + Postgres)
docker compose build             # rebuild Docker image
```

**just recipes** (`.justfile`):
```bash
just test          # uv sync + pytest
just check         # ruff check
just format        # ruff format
just prcheck       # check + format + test
just run <args>    # uv run mechabellum-replay-parser <args>
just build         # uv build
just bump-version <type>  # bumpver + uv sync + commit
```

---

## Knowledge RAG

`game_knowledge.md` is parsed into **95 chunks** by `knowledge/parser.py`, tagged by topic (units, techs, constructions, strategies, etc.).

`KnowledgeRetriever.retrieve(state, features)` selects the most relevant chunks based on:
- Enemy unit names (unit-specific chunks)
- Threat keys from TacticalFeatures
- Active tech names
- Player unit names

Relevant chunks are injected into the Planner and Judge prompts (replaces full `game_knowledge.md` injection).

---

## Parsed JSON Structure

```json
{
  "metadata": {"version": "1.x.x", "match_mode": "VS_1_1"},
  "teams": [["Player1"], ["Player2"]],
  "last_round": 5,
  "rounds": [
    {
      "round": 5,
      "fight_result": {"winner": "Player1"},
      "players": {
        "Player1": {
          "hp": 3,
          "fight_outcome": "win",
          "army_value": 1450,
          "officers": [],
          "commander_skills": [],
          "contraptions": [],
          "constructions": [
            {"type": "tower", "index": 0, "position": {"x": 100, "y": -270}}
          ],
          "active_techs": [{"unit": "arclight", "tech": "Range enhancement"}],
          "units": [
            {
              "name": "crawler", "unit_id": 10, "index": 0,
              "level": 2, "position": {"x": -40, "y": -80},
              "equipment": null, "sell_supply": 60
            }
          ],
          "shop": {
            "unlocked": ["crawler", "arclight"],
            "locked": ["marksman", "phoenix"],
            "buys_remaining": 3,
            "unlocks_remaining": 1
          }
        }
      }
    }
  ]
}
```
