# Round492 Observation Target-End Gap Plan

Date: 2026-07-04

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Machine/task: `office_desktop` / `data_pipeline`

## Status

- Project completion gate remains at 98%.
- Profit factor mining remains blocked by `pre-alpha`.
- Current validated observation source remains Round478: 5 / 20 fills, deficit 15.
- This round did not start a new alpha search; it clarified the observation-continuation plan for a known provider target-end gap.

## Root Cause

Round491 produced a clean recent-refresh evidence pack for 2026-05-06 to 2026-07-03, but the continuation planner only recognized required-asset gaps when the pack listed explicit `required_asset_missing_trade_dates`.

The Round491 failure shape is different:

- `target_end_covered=false`
- Required asset `CN_ETF_XSHE_160615` starts at the target start.
- The same asset stops at 2026-07-02, before the requested target end 2026-07-03.
- There is no middle-window missing-trade-date recovery split to generate.

Before this round, `scripts/run_observation_continuation_plan.py` reported `gap_recovery.status=not_applicable` for that pack, which made the next step less explicit.

## Change

`scripts/run_observation_continuation_plan.py` now detects required-asset target-end gaps and emits:

- `gap_recovery.status=target_end_gap_available`
- A `latest_required_asset_clean_window` from the recent-refresh target start to the latest common clean required-asset end
- `next_actions[0].action=wait_for_required_asset_target_end`

For the real Round491 pack, the generated action is:

- Wait for `CN_ETF_XSHE_160615` to cover 2026-07-03, or rerun only through latest clean end 2026-07-02.
- Latest clean command window: 2026-05-06 to 2026-07-02.

## Verification

Regression test added:

- `tests/unit/test_observation_continuation_plan.py::ObservationContinuationPlanTests::test_gap_recovery_surfaces_required_asset_target_end_gap`

Fresh checks:

- Targeted red test failed before the implementation with `not_applicable != target_end_gap_available`.
- After implementation, targeted test passed.
- Full observation-continuation-plan test file passed: 6 / 6.
- Real Round491 planner run emitted `target_end_gap_available` and `wait_for_required_asset_target_end`.

## Decision

Do not run another generic observation continuation over the older 2026-03-23 to 2026-06-26 recommendation when the active blocker is the later 2026-07-03 target-end gap. Wait for a valid `160615.SZ` provider row on 2026-07-03 or a later clean execution date, then rerun the after-gap extension. Alpha mining remains blocked until the completion gate clears.
