# CN Stock External Feed Seventh Monthly Shard - Round179

Date: 2026-06-23

## Scope

Round179 continued controlled long-cycle external-feed backfill for CN stock factor mining.

Shard:

- Start: `2025-06-01`
- End: `2025-06-30`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202506/external_feed_ingestion_report.json`
- Progress log: `data/reports/round179_external_feed_seventh_monthly_shard_202506_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 4
- Warn: 1
- Fail: 0
- Progress events: 165
- Stderr: empty

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 82190 | 4113 entities, no lag violations, no duplicate keys. |
| `external_hk_hold` | pass | 3788 | One effective primary observation date: 2025-06-30, available on 2025-07-01. |
| `external_hsgt_flow` | pass | 20 | Available dates from 2025-06-04 to 2025-07-01. |
| `external_index_state` | pass | 20 | One index entity, no PIT lag violations. |
| `external_macro_rates` | warn | 20 | SHIBOR present; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round179_external_feed_seven_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 1734049
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 146 | 146 | n/a |
| `margin_balance_crowding_reversal_20` | 146 | 630846 | 4583 |
| `margin_financing_acceleration_exhaustion_20` | 146 | 630846 | 4583 |
| `shibor_liquidity_tightening_regime_20` | 145 | 145 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed improved to 3 primary observation dates, still below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` resolves with 140 observation dates, but HK hold primary feed has only 3 observation dates. |

## Decision

Round179 improved long-cycle coverage and added one more HK hold primary observation date, but it does not change promotion status.

The correct interpretation remains:

- External margin, SHIBOR, and index-state seeds are matrix-ready.
- Northbound hold seeds are not matrix-ready because the primary holding feed is too sparse.
- Join smoke is not alpha evidence.
- No cost/capacity walk-forward, redundancy audit, regime audit, or holdout audit was run.

Next controlled direction: continue monthly backfill with the next shard, `2025-05`, then run the Round178-180 three-round review after Round180 completes.
