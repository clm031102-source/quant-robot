# CN Stock External Feed Fourth Monthly Shard Round176

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round175 made three external-feed seeds history-ready but left SHIBOR at 59 observation dates. Round176 added the 2025-09 shard to push SHIBOR past the 60-observation threshold and continue diagnosing northbound hold coverage.

## Shard Command

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-09-01 --end-date 2025-09-30 --output-dir data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-copy-dir data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623\shard_202509 --execute-write-processed --progress-jsonl data\reports\round176_external_feed_fourth_monthly_shard_202509_20260623\progress.jsonl
```

## Ingestion Result

- Progress events: 181
- Feed summary: 4 pass, 1 warn, 0 fail
- `external_margin_detail`: 91,510 rows, 2025-09-01 to 2025-09-30, 0 lag violations, 0 missing `available_date`
- `external_hsgt_flow`: 21 rows, 2025-09-01 to 2025-09-30, 0 lag violations, 0 missing `available_date`
- `external_index_state`: 22 rows, 2025-09-01 to 2025-09-30, 0 lag violations, 0 missing `available_date`
- `external_macro_rates`: 22 rows, warn because LPR remained missing/cached empty
- `external_hk_hold`: 3,340 rows, only 2025-09-30 after CN-stock filtering

## Four-Month Join Smoke Result

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round176_external_feed_four_month_join_smoke_20260623
```

Result:

- Seed count: 6
- Joined rows: 924,127
- `available_date` violations: 0
- Raw same-day/future date violations: 0
- Pass: 4
- Insufficient history: 2
- Warn: 0
- Fail: 0

History-ready seeds:

- `index_location_value_liquidity_regime_20`: 82 observation dates
- `margin_balance_crowding_reversal_20`: 82 observation dates, 363,335 joined rows, 4,561 symbols
- `margin_financing_acceleration_exhaustion_20`: 82 observation dates, 363,335 joined rows, 4,561 symbols
- `shibor_liquidity_tightening_regime_20`: 81 observation dates

Still blocked:

- `northbound_hold_ratio_accumulation_20`: only 2 primary observation dates.
- `northbound_hold_accumulation_flow_regime_20`: only 2 primary observation dates, despite 77 secondary `north_money` dates.
- LPR-dependent work remains blocked by missing/cached-empty coverage.

## Decision

Round176 makes four of six seeds matrix-ready, but this remains data readiness only. No external-feed IC, portfolio grid, promotion, Sharpe, or win-rate claim is allowed from four recent months.

HK hold appears to behave as a low-frequency/month-end holding feed after CN-stock filtering. It should not be treated as daily northbound holding data without a dedicated coverage and frequency audit.

## Next Direction

Round177 should execute the 2025-08 shard with progress JSONL. After Round177, perform the next three-round review for Round175-177 before deciding whether to continue backfill, repair HK hold/LPR coverage, or begin a carefully labelled long-cycle readiness audit.
