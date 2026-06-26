# CN Stock External Feed Round190 2024-07 Shard

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor infrastructure, not CN ETF rotation
- Promotion allowed: no

## What Ran

Round190 backfilled the 2024-07 monthly shard for processed Tushare external feeds under `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`.

Shard ingestion report:

- Feed count: 5
- Pass/warn/fail: 4 / 1 / 0
- `external_margin_detail`: 85,836 rows, 3,926 entities, 32 missing `rqye` and 32 missing `rzrqye`
- `external_hk_hold`: 73,605 canonical CN-stock rows, 3,355 entities, 17,378 non-CN rows dropped
- `external_hsgt_flow`: 22 rows
- `external_index_state`: 23 rows
- `external_macro_rates`: 23 rows, SHIBOR present, `lpr_1y` and `lpr_5y` still fully missing

## Join Smoke

The full-window join smoke used `configs/external_feed_factor_seed_preregistration_round170_20260623.json` and wrote:

- `data/reports/round190_external_feed_202407_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 6
- Insufficient history: 0
- Fail: 0
- Joined rows: 4,262,401
- `available_date` violations: 0
- same-day/future raw-date violations: 0

History-ready matrix seeds:

- `margin_balance_crowding_reversal_20`: 347 observation dates, 1,452,449 joined rows, 4,660 symbols
- `margin_financing_acceleration_exhaustion_20`: 347 observation dates, 1,452,449 joined rows, 4,660 symbols
- `northbound_hold_ratio_accumulation_20`: 40 primary HK-hold observation dates, 136,475 joined rows, 3,980 symbols
- `northbound_hold_accumulation_flow_regime_20`: 40 primary HK-hold observation dates, 333 secondary HSGT-flow observation dates, 1,220,320 joined rows, 3,980 symbols
- `shibor_liquidity_tightening_regime_20`: 340 observation dates, 340 joined rows
- `index_location_value_liquidity_regime_20`: 368 observation dates, 368 joined rows

## Coverage Audit

Coverage audit wrote:

- `data/reports/round190_external_feed_hk_hold_lpr_coverage_audit_after_202407_shard_20260623/external_feed_coverage_audit.json`

Results:

- `external_hk_hold`: pass
  - 40 observation dates
  - 134,461 rows
  - 3,980 symbols
  - median gap 1 day, max gap 92 days
  - detected frequency: daily_or_near_daily
- `external_macro_rates`: blocked by `lpr_non_missing_coverage_below_threshold`
  - 340 macro observation dates
  - 340 complete SHIBOR rows
  - 0 non-null LPR rows

## Decision

Round190 changed the next step. HK hold is no longer blocked by minimum observation coverage, so blindly continuing monthly backfill would be lower value than testing the newly unblocked northbound seeds.

Next controlled step:

- Build or reuse an external-feed IC/quantile/turnover prescreen for the two northbound seeds.
- Treat the test as preregistered research screening, not portfolio promotion.
- Keep LPR-dependent policy-liquidity factors blocked.
- Do not run portfolio grids before IC, quantile monotonicity, turnover decay, redundancy, and capacity/cost checks.

This round still did not discover or promote a profitable factor. It only unlocked a new testable factor family path.
