# Round489 Post-Refresh Window Propagation

Date: 2026-07-04

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Machine/task: `office_desktop` / `data_pipeline`

## Status

- Project completion gate remains at 98%.
- Profit factor mining remains blocked by `pre-alpha`.
- Current validated observation source remains Round478: 5 / 20 fills, deficit 15.

## Root Cause

Round488 made gap recovery explicit, but extending the post-gap data window did not increase observation fills. The reason was two-layered:

1. `scripts/run_post_refresh_replay.py` did not pass the recent refresh `target_window` into Daily Ops.
2. `scripts/run_daily_ops.py` did not expose `start_date` / `end_date` for paper simulation, so `run_paper_simulation` received `start_date=null` and `end_date=null`.

The profile observation window comes from the paper simulation `equity_curve.csv`, not directly from the recent refresh pack. Without explicit simulation dates, the replay artifact could look refreshed while the simulated observation curve still ended at 2026-06-26.

## Changes

- `scripts/run_daily_ops.py`
  - Added `start_date` and `end_date`.
  - Passes `run_date` as signal snapshot `as_of_date`.
  - Passes `start_date` and `end_date` into `run_simulation`.
- `scripts/run_post_refresh_replay.py`
  - Extracts recent refresh `target_window.start_date` and `target_window.end_date`.
  - Passes those dates into Daily Ops.
- Tests
  - `tests/unit/test_daily_ops_cli.py` now verifies Daily Ops forwards observation-window dates.
  - `tests/unit/test_post_refresh_replay.py` now verifies post-refresh replay forwards the recent refresh window.

## Real Evidence

Quant PM startup gate passed:

- Status: `ready`
- Primary market: `CN_ETF`
- Blockers: none

After-gap extension attempt:

- Window: 2026-05-06 to 2026-07-03
- Report: `data/reports/round489_observation_postgap_extended_20260704/recent_data_refresh`
- Status: `data_quality_blocked`
- Required asset: `CN_ETF_XSHE_160615`
- Required asset rows: 41 / 42
- Required asset latest date: 2026-07-02
- Blockers: `required_assets_not_covered`, `target_end_not_covered`, `missing_date_rows`

Truncated latest clean window:

- Window: 2026-05-06 to 2026-07-02
- Report: `data/reports/round489_observation_postgap_to_20260702_20260704/recent_data_refresh`
- Status: `completed`
- Required asset coverage: 41 / 41

Post-fix replay on the clean window:

- Report: `data/reports/round489_observation_postgap_to_20260702_windowed_20260704`
- Paper simulation request now records:
  - `start_date`: 2026-05-06
  - `end_date`: 2026-07-02
- Replay status: `replay_blocked`
- Replay blocker: `minimum_fills_observed`
- Observation sufficiency: 5 / 20 fills, deficit 15

## Decision

The date propagation bug is fixed, but observation sufficiency still does not clear. The next rebalance/fill opportunity needs the 2026-07-03 execution date, and `CN_ETF_XSHE_160615` is not covered on that date in the current Tushare refresh.

Do not start alpha mining. The next useful data action is to rerun the after-gap extension once the required asset covers 2026-07-03 or a later clean execution date.
