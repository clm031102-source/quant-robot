# CN Stock External Feed Fifth Monthly Shard Round177

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round176 made four of six external-feed seeds history-ready. Round177 added the 2025-08 shard before the required three-round review for Round175-177.

## Shard Command

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-08-01 --end-date 2025-08-31 --output-dir data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-copy-dir data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623\shard_202508 --execute-write-processed --progress-jsonl data\reports\round177_external_feed_fifth_monthly_shard_202508_20260623\progress.jsonl
```

## Ingestion Result

- Progress events: 173
- Feed summary: 3 pass, 2 warn, 0 fail
- `external_margin_detail`: 87,224 rows, 2025-08-01 to 2025-08-29, 0 lag violations, 0 missing `available_date`
- `external_hsgt_flow`: 21 rows, 2025-08-01 to 2025-08-29, 0 lag violations, 0 missing `available_date`
- `external_index_state`: 21 rows, 2025-08-01 to 2025-08-29, 0 lag violations, 0 missing `available_date`
- `external_macro_rates`: 21 rows, warn because LPR remained missing/cached empty
- `external_hk_hold`: warn, 0 CN-stock rows after filtering

## Five-Month Join Smoke Result

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round177_external_feed_five_month_join_smoke_20260623
```

Result:

- Seed count: 6
- Joined rows: 1,098,817
- `available_date` violations: 0
- Raw same-day/future date violations: 0
- Pass: 4
- Insufficient history: 2
- Warn: 0
- Fail: 0

History-ready seeds:

- `index_location_value_liquidity_regime_20`: 103 observation dates
- `margin_balance_crowding_reversal_20`: 103 observation dates, 450,659 joined rows, 4,562 symbols
- `margin_financing_acceleration_exhaustion_20`: 103 observation dates, 450,659 joined rows, 4,562 symbols
- `shibor_liquidity_tightening_regime_20`: 102 observation dates

Still blocked:

- `northbound_hold_ratio_accumulation_20`: only 2 primary observation dates.
- `northbound_hold_accumulation_flow_regime_20`: only 2 primary observation dates, despite 98 secondary `north_money` dates.
- LPR-dependent work remains blocked by missing/cached-empty coverage.

## Decision

Round177 adds more long-cycle coverage but does not change the promotion decision. Four seeds are matrix-ready, not alpha-ready. Northbound hold and LPR factors remain blocked. No IC, portfolio, Sharpe, win-rate, or promotion claim is allowed from this coverage-only evidence.
