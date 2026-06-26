# CN Stock External Feed Third Monthly Shard Round175

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round174 made two margin external-feed seeds history-ready but left index-state and SHIBOR below their 60-observation threshold. Round175 added the 2025-10 shard to push cumulative coverage toward 60 observation dates.

## Runtime Issue And Fix

The first 2025-10 attempt failed before progress events because Tushare `trade_cal` transiently returned no open trade dates. A direct repeat of the same calendar window returned 27 open days, so this was treated as an external transient empty response.

Fix:

- Added retry handling for empty trade-calendar responses in `run_tushare_external_feed_ingest`.
- Added a regression test for one empty calendar response followed by a valid response.
- Field-missing calendar responses still fail immediately.

## Retry Shard Command

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-10-01 --end-date 2025-10-31 --output-dir data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-copy-dir data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623\shard_202510 --execute-write-processed --progress-jsonl data\reports\round175_external_feed_third_monthly_shard_202510_retry_20260623\progress.jsonl
```

## Ingestion Result

- Progress events: 141
- Feed summary: 3 pass, 2 warn, 0 fail
- `external_margin_detail`: 71,682 rows, 2025-10-09 to 2025-10-31, 0 lag violations, 0 missing `available_date`
- `external_hsgt_flow`: 16 rows, 2025-10-09 to 2025-10-31, 0 lag violations, 0 missing `available_date`
- `external_index_state`: 17 rows, 2025-10-09 to 2025-10-31, 0 lag violations, 0 missing `available_date`
- `external_macro_rates`: 17 rows, warn because LPR remained missing/cached empty
- `external_hk_hold`: warn, 0 CN-stock rows after filtering

## Three-Month Join Smoke Result

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round175_external_feed_three_month_join_smoke_20260623
```

Result:

- Seed count: 6
- Joined rows: 520,489
- `available_date` violations: 0
- Raw same-day/future date violations: 0
- Pass: 3
- Insufficient history: 3
- Warn: 0
- Fail: 0

History-ready seeds:

- `index_location_value_liquidity_regime_20`: 60 observation dates
- `margin_balance_crowding_reversal_20`: 60 observation dates, 256,860 joined rows, 4,316 symbols
- `margin_financing_acceleration_exhaustion_20`: 60 observation dates, 256,860 joined rows, 4,316 symbols

Still blocked:

- `shibor_liquidity_tightening_regime_20`: 59 observation dates, one short of the 60-day threshold.
- `northbound_hold_ratio_accumulation_20`: only 1 primary observation date.
- `northbound_hold_accumulation_flow_regime_20`: only 1 primary observation date; secondary `north_money` coverage is 56 observation dates.
- LPR-dependent work remains blocked by missing/cached-empty coverage.

## Decision

Round175 materially improved matrix readiness: three of six seeds now pass the coverage/PIT join smoke. It still does not prove alpha, profitability, Sharpe, win rate, or tradability. No portfolio grid or promotion is allowed from three months of coverage.

## Next Direction

Round176 should execute the 2025-09 shard with progress JSONL. This should make SHIBOR history-ready and provide another checkpoint for HK hold and LPR coverage. After Round176, continue controlled backfill rather than running short-window external-feed IC or portfolio tests.
