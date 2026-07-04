# Round501 Observation Sufficiency Cleared

Date: 2026-07-04

## Summary

Round501 cleared the remaining paper-observation sample gate for the active CN ETF paper lane.

Key evidence:

- Fixed Tushare `fund_basic` mapping so `ETF Link (LOF)` funds are not classified as ETFs.
- Enriched `run_required_asset_target_end_check.py` with `fund_basic` metadata, so provider target-end gaps can distinguish missing ETF rows from old non-ETF required assets.
- Added rotation-membership excluded-asset handling to recent-refresh coverage so structurally excluded old required assets do not keep blocking a refreshed provider universe.
- Round497 refresh cleared the stale target-end loop and replayed the active profile on 2026-07-03.
- Round498 extended observation to 2026-04-06 through 2026-07-03 and lifted fills to 13 / 20.
- Round500 extended to 2026-03-01 through 2026-07-03 and lifted fills to 18 / 20.
- Round501 extended to 2026-02-01 through 2026-07-03 and cleared the gate with 25 / 20 fills.

## Generated Evidence

Generated outputs remain local under ignored `data/` paths:

- `data/reports/round497_recent_data_refresh_lof_filter_20260704/recent_data_refresh_pack.json`
- `data/reports/round497_post_refresh_replay_lof_filter_20260704/post_refresh_replay_pack.json`
- `data/reports/round498_recent_data_refresh_observation_extend_20260704/recent_data_refresh_pack.json`
- `data/reports/round498_observation_sufficiency_observation_extend_20260704/observation_sufficiency_pack.json`
- `data/reports/round500_observation_sufficiency_long_observation_20260704/observation_sufficiency_pack.json`
- `data/reports/round501_recent_data_refresh_longer_observation_20260704/recent_data_refresh_pack.json`
- `data/reports/round501_post_refresh_replay_longer_observation_20260704/post_refresh_replay_pack.json`
- `data/reports/round501_observation_sufficiency_longer_observation_20260704/observation_sufficiency_pack.json`

## Completion Gate Impact

Default `pre-alpha` discovery now selects the Round501 sufficient observation pack:

- Recent data refresh: `completed`
- Target-end gap: none
- Observation sufficiency: `sufficient`
- Observed fills: 25
- Required fills: 20
- Fill deficit: 0

Remaining blockers are Git integration only:

- current branch is not `main`
- two remote topic branches remain
- worktree must be committed and pushed

## Decision

Alpha mining is still blocked until laptop-owned `main` integration and remote topic branch cleanup are complete. Once laptop/project_sync merges this topic branch, verifies `main`, pushes `main`, and cleans the remote topic branches, the completion gate should allow factor mining.
