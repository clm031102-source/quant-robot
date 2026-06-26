# CN Stock External Feed Round189 2024-08 Shard

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor infrastructure, not CN ETF rotation
- Promotion allowed: no

## What Ran

Round189 backfilled the 2024-08 monthly shard for processed Tushare external feeds under `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`. The run was research-to-review only, with no broker, account, order, or live-trading access.

Shard ingestion report:

- Feed count: 5
- Pass/warn/fail: 4 / 1 / 0
- `external_margin_detail`: 86,124 rows, 3,921 entities, 34 missing `rqye` and 34 missing `rzrqye`
- `external_hk_hold`: 40,112 canonical CN-stock rows, 3,346 entities, 17,430 non-CN rows dropped
- `external_hsgt_flow`: 21 rows
- `external_index_state`: 22 rows
- `external_macro_rates`: 22 rows, SHIBOR present, `lpr_1y` and `lpr_5y` still fully missing

## Join Smoke

The full-window join smoke used `configs/external_feed_factor_seed_preregistration_round170_20260623.json` and wrote:

- `data/reports/round189_external_feed_202408_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Joined rows: 3,932,590
- `available_date` violations: 0
- same-day/future raw-date violations: 0

History-ready matrix seeds:

- `margin_balance_crowding_reversal_20`: 325 observation dates, 1,362,631 joined rows, 4,651 symbols
- `margin_financing_acceleration_exhaustion_20`: 325 observation dates, 1,362,631 joined rows, 4,651 symbols
- `shibor_liquidity_tightening_regime_20`: 317 observation dates, 317 joined rows
- `index_location_value_liquidity_regime_20`: 345 observation dates, 345 joined rows

Still blocked or insufficient-history seeds:

- `northbound_hold_ratio_accumulation_20`: 18 primary HK-hold observation dates, 62,620 joined rows, 3,972 symbols
- `northbound_hold_accumulation_flow_regime_20`: 18 primary HK-hold observation dates, 311 secondary HSGT flow observation dates, 1,144,046 joined rows, 3,972 symbols

## Coverage Audit

Coverage audit wrote:

- `data/reports/round189_external_feed_hk_hold_lpr_coverage_audit_after_202408_shard_20260623/external_feed_coverage_audit.json`

Results:

- `external_hk_hold`: blocked by `hk_hold_observation_dates_below_minimum`
  - 18 observation dates
  - 60,856 rows
  - 3,972 symbols
  - median gap 1 day, max gap 92 days
  - detected frequency: daily_or_near_daily
- `external_macro_rates`: blocked by `lpr_non_missing_coverage_below_threshold`
  - 317 macro observation dates
  - 317 complete SHIBOR rows
  - 0 non-null LPR rows

## Process Fix

Round189 exposed a path-footgun: `run_external_feed_factor_matrix_join_smoke.py --processed-root` and `run_external_feed_coverage_audit.py --processed-root` previously expected the parent directory of `processed`, while the option name also plausibly suggested the `processed` child directory. Passing the child directory produced a false all-empty join-smoke result.

The readers now normalize either input style:

- parent root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- processed child root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623/processed`

Regression tests were added for both join smoke and coverage audit.

## Conclusion

Round189 did not discover or promote any profitable factor. It improved long-cycle external-feed readiness:

- Four external-feed seeds are matrix-ready but remain non-alpha evidence until IC, quantile, turnover, cost/capacity, redundancy, regime, and walk-forward gates run.
- HK hold improved materially from sparse observations to near-daily segments, but only 18 observation dates are available, so northbound hold factors remain blocked.
- LPR remains unusable because both LPR columns are fully missing.

Next controlled step: run Round190 with the 2024-07 monthly shard, continue margin/SHIBOR/index backfill, and retest whether HK hold reaches the minimum observation threshold before any northbound IC work.
