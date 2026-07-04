# Round488 Observation Gap Recovery Plan

Date: 2026-07-04

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Machine/task: `office_desktop` / `data_pipeline`

## Status

- Project completion gate remains at 98%.
- Profit factor mining remains blocked by `pre-alpha`.
- Current validated observation source remains Round478: 5 / 20 fills, deficit 15.

## What Changed

- `src/quant_robot/data/quality_report.py` now records `coverage_by_asset[].missing_trade_dates`.
- `src/quant_robot/ops/recent_data_refresh.py` now propagates required-asset missing dates into:
  - `coverage.required_asset_coverage[].missing_trade_dates`
  - `coverage.required_asset_missing_trade_dates`
- `scripts/run_observation_continuation_plan.py` now accepts `--recent-data-refresh-pack` and emits `gap_recovery` windows plus full per-window command sets.

## Real Evidence

Quant PM startup gate passed:

- Status: `ready`
- Primary market: `CN_ETF`
- Blockers: none

Full recommended observation window retry:

- Window: 2026-03-23 to 2026-06-26
- Report: `data/reports/round488_observation_continuation_retry_with_dates_20260704/recent_data_refresh`
- Status: `data_quality_blocked`
- Required asset: `CN_ETF_XSHE_160615`
- Coverage: 64 / 65 rows
- Missing trade date: 2026-04-30

Post-gap continuous window:

- Window: 2026-05-06 to 2026-06-26
- Report: `data/reports/round488_observation_postgap_20260704`
- Recent refresh status: `completed`
- Required asset coverage: 37 / 37 rows
- Post-refresh replay status: `replay_blocked`
- Replay blocker: `minimum_fills_observed`
- Observation sufficiency: 5 / 20 fills, deficit 15

Gap-aware continuation plan:

- Input recent refresh pack: `data/reports/round488_observation_continuation_retry_with_dates_20260704/recent_data_refresh/recent_data_refresh_pack.json`
- Recovery status: `gap_recovery_available`
- Recovery windows:
  - `before_missing_trade_date`: 2026-03-23 to 2026-04-29
  - `after_missing_trade_date`: 2026-05-06 to 2026-06-26
- The plan emits full command sets for each recovery window: startup gate, recent refresh, post-refresh replay, observation sufficiency, then `pre-alpha`.

## Decision

Round488 improves the continuation workflow but does not clear observation sufficiency. The single required-asset gap on 2026-04-30 still prevents a clean full-window replay. The post-gap replay proves the later continuous window is data-ready and paper-workflow-ready, but the fill gate remains 5 / 20.

Do not start alpha mining. Continue with gap-aware paper-observation extension or wait for the missing required-asset bar to become available, then rerun `pre-alpha`.
