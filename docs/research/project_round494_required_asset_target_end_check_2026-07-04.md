# Round494 Required-Asset Target-End Check

Date: 2026-07-04

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Machine/task: `office_desktop` / `data_pipeline`, then `factor_batch` sync

## Status

- Project completion gate remains at 98%.
- Profit factor mining remains blocked by `pre-alpha`.
- Current validated observation source remains Round478: 5 / 20 fills, deficit 15.
- This round did not start factor mining; it turned the target-end wait into an executable provider check.

## Change

New script:

```powershell
python scripts\run_required_asset_target_end_check.py --machine office_desktop --task data_pipeline --recent-data-refresh-pack data\reports\round491_recent_data_refresh_postgap_to_20260703_clean_action_20260704\recent_data_refresh_pack.json --execute
```

The script reads a recent-refresh pack, extracts required-asset target-end gaps, checks the provider target-end date, and emits the next action:

- `target_end_missing`: recheck later.
- `target_end_available`: rerun recent refresh through the target end when a profile-observation pack is supplied.

`scripts/run_project_completion_gate.py` now points `wait_for_required_asset_target_end` to this script instead of the broader observation-continuation planner.

## Real Provider Check

Quant PM startup gate passed before the provider query:

- Status: `ready`
- Primary market: `CN_ETF`
- Blockers: none

Real target-end check from the Round491 pack:

- Source pack: `data/reports/round491_recent_data_refresh_postgap_to_20260703_clean_action_20260704/recent_data_refresh_pack.json`
- Target window: 2026-05-06 to 2026-07-03
- Required asset: `CN_ETF_XSHE_160615`
- Required symbol: `160615.SZ`
- Latest clean end: 2026-07-02
- Provider target-end rows on 2026-07-03: 2,047
- `160615.SZ` target rows on 2026-07-03: 0
- Status: `target_end_missing`

## Verification

Regression tests added:

- `tests/unit/test_required_asset_target_end_check.py`
- Completion-gate command assertion updated to require `scripts/run_required_asset_target_end_check.py`.

Fresh checks:

- New script and completion-gate target tests passed: 4 / 4.
- Full related test set passed before sync.
- Real script run returned `target_end_missing` with `target_rows=0`.
- Real `pre-alpha` output now points to the new target-end check script.

## Decision

Do not rerun the after-gap refresh through 2026-07-03 until the target-end check reports `target_end_available`. Do not start alpha mining. The next observation-data action is a repeat of the target-end check after provider data changes, followed by recent refresh, post-refresh replay, and observation sufficiency only if `160615.SZ` appears.
