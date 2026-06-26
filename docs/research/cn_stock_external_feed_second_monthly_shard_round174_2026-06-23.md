# CN Stock External Feed Second Monthly Shard Round174

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round173 proved the first monthly shard could run with observable progress logs and 0 PIT join violations, but all six pre-registered external-feed seeds still had insufficient history. Round174 added the next monthly shard, 2025-11-01 through 2025-11-30, into the same processed root.

## Shard Command

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-11-01 --end-date 2025-11-30 --output-dir data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-copy-dir data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623\shard_202511 --execute-write-processed --progress-jsonl data\reports\round174_external_feed_second_monthly_shard_202511_20260623\progress.jsonl
```

## Ingestion Result

- Progress events: 165
- Feed summary: 3 pass, 2 warn, 0 fail
- `external_margin_detail`: 85,257 rows, 2025-11-03 to 2025-11-28, 0 lag violations, 0 missing `available_date`
- `external_hsgt_flow`: 19 rows, 2025-11-03 to 2025-11-28, 0 lag violations, 0 missing `available_date`
- `external_index_state`: 20 rows, 2025-11-03 to 2025-11-28, 0 lag violations, 0 missing `available_date`
- `external_macro_rates`: 19 rows, warn because LPR remained missing; one SHIBOR day returned 0 rows
- `external_hk_hold`: warn, 0 CN-stock rows after filtering under the current endpoint response shape

## Two-Month Join Smoke Result

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round174_external_feed_two_month_join_smoke_20260623
```

Result:

- Seed count: 6
- Joined rows: 373,999
- `available_date` violations: 0
- Raw same-day/future date violations: 0
- Pass: 2
- Insufficient history: 4
- Warn: 0
- Fail: 0

The two `history_ready` seeds are:

- `margin_balance_crowding_reversal_20`: 43 observation dates, 183,632 joined rows, 4,287 symbols
- `margin_financing_acceleration_exhaustion_20`: 43 observation dates, 183,632 joined rows, 4,287 symbols

Still blocked:

- Index-state and SHIBOR seeds need 60 observation dates; current coverage is 42-43.
- Northbound hold seeds still have only 1 primary observation date because `external_hk_hold` retained CN-stock rows only on 2025-12-31 across the first two shards.
- LPR-dependent work remains blocked until non-missing LPR coverage is proven.

## Decision

Round174 produced useful data-pipeline progress and made two margin seeds matrix-ready. It is still not factor profitability evidence. Do not run external-feed portfolio grids or claim alpha from two months of data.

## Next Direction

Round175 should execute the 2025-10 monthly shard with progress logging, then rerun join smoke. That should move index-state and SHIBOR feeds near or above the 60-observation history threshold while continuing to diagnose HK hold and LPR coverage.
