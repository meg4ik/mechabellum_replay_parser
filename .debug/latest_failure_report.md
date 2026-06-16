# Latest Recommendation Debug Report
## Replay / Round

- **Match mode:** VS_1_1
- **Round:** 2
- **Player:** Player1
- **Enemies:** Player2
- **Supply:** 200
- **My HP:** 3
- **My units:** ['crawler', 'crawler']

## Coordinate Frame

- **Side:** negative_y
- **Front Y:** -16
- **Back Y:** -304
- **X range:** [-294 .. 294]

## Main Threats

> *No threats detected.*

## Legal Actions

- `unlock_mustang` (unlock_unit) cost=0
- `unlock_wasp` (unlock_unit) cost=0
- `buy_arclight` (buy_unit) cost=100
- `buy_crawler` (buy_unit) cost=100
- `keep_crawler_0` (keep_unit) cost=0
- `move_crawler_0` (move_unit) cost=0
- `keep_crawler_1` (keep_unit) cost=0
- `move_crawler_1` (move_unit) cost=0
- `skip` (skip) cost=0

## Tactical Bundles

- **Hold position** (theme=`safe_default`)  cost=0  actions=['keep_crawler_0', 'keep_crawler_1', 'skip']

## Planner Plans

- **[plan_buy_arclight]** Buy Arclight to counter air threat  cost=100  actions=['buy_arclight']

## Validation Errors

- ✓ `plan_buy_arclight`

## Resolved Placement

- ?  x=0 y=-304  lane=center depth=back

## Plan Scores

- `plan_buy_arclight`  total=0.665  threats=0.70  supply=0.70  legality_penalty=0.00

## Judge Selection

- **Selected plan:** `plan_buy_arclight`
- **Confidence:** 0.8
- **Main reason:** Selected automatically: highest-scoring valid plan (Judge LLM unavailable).

## Final Recommendation

**Summary:** Selected automatically: highest-scoring valid plan (Judge LLM unavailable).

**Coach text:**
Round 2 plan for Player1
Tempo: unknown  |  Posture: aggro

** Buy Arclight to counter air threat **
Goal: Counter enemy air pressure
Why: Arclight has strong anti-air capabilities.

Decision: Selected automatically: highest-scoring valid plan (Judge LLM unavailable).

Placement:
  arclight -> (0, -304) Lane.CENTER_Depth.BACK [PlacementAction.NEW]

Risks: Arclight is expensive

**Placement items:** 1

## Stage Timings

- `state_view_ms`: 0 ms
- `features_ms`: 0 ms
- `legal_actions_ms`: 0 ms
- `tactical_bundles_ms`: 0 ms
- `knowledge_retrieval_ms`: 0 ms
- `planner_llm_ms`: 0 ms
- `validator_ms`: 0 ms
- `plan_scorer_ms`: 0 ms
- `judge_llm_ms`: 7 ms
- `placement_resolver_ms`: 0 ms

## Suspected Failure Stage

**feature_extractor** — no threats detected (check FeatureExtractor signals)

