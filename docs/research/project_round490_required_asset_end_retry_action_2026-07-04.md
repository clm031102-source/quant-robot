# Round490 Required-Asset End Retry Action

Date: 2026-07-04

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Machine/task: `office_desktop` / `data_pipeline`

## Status

- Project completion gate remains at 98%.
- Profit factor mining remains blocked by `pre-alpha`.
- Current validated observation source remains Round478: 5 / 20 fills, deficit 15.

## Real Retry

Quant PM startup gate passed:

- Status: `ready`
- Primary market: `CN_ETF`
- Blockers: none

After-gap latest execution-date retry:

- Window: 2026-05-06 to 2026-07-03
- Report: `data/reports/round490_observation_postgap_to_20260703_retry_20260704/recent_data_refresh`
- Status: `data_quality_blocked`
- Required asset: `CN_ETF_XSHE_160615`
- Required asset rows: 41 / 42
- Required asset latest date: 2026-07-02
- Blockers:
  - `required_assets_not_covered`
  - `target_end_not_covered`
  - `missing_date_rows`

## Change

`src/quant_robot/ops/recent_data_refresh.py` now emits a specific next action when required assets are covered at the target start but stop before the requested target end:

- Action: `rerun_recent_refresh_to_latest_required_asset_end`
- Command shape: `python scripts\run_recent_data_refresh.py --machine <machine> --start-date <target_start> --end-date <latest_required_asset_end> --execute`
- Reason includes the limiting required asset IDs and latest clean target end.

This avoids repeating a known-bad target end while still preserving the paper-only safety boundary.

## Decision

The latest required asset coverage still stops at 2026-07-02, so the 2026-07-03 execution-date replay cannot proceed. Do not start alpha mining. Continue retrying the after-gap extension once `CN_ETF_XSHE_160615` covers 2026-07-03 or a later clean execution date.
