# CN Stock External Feed Tenth Monthly Shard - Round182

Date: 2026-06-23

## Scope

Round182 continued controlled long-cycle external-feed backfill for CN stock factor mining.

Shard:

- Start: `2025-03-01`
- End: `2025-03-31`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202503/external_feed_ingestion_report.json`
- Progress log: `data/reports/round182_external_feed_tenth_monthly_shard_202503_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 4
- Warn: 1
- Fail: 0
- Progress events: 173
- Stderr: empty

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 85301 | Margin-detail shard wrote normally. |
| `external_hk_hold` | pass | 3366 | Canonical CN-stock output returned usable rows for one additional primary observation month. |
| `external_hsgt_flow` | pass | 21 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 21 | Index-state rows available for the shard. |
| `external_macro_rates` | warn | 21 | SHIBOR present; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round182_external_feed_ten_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 2448110
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 207 | 207 | n/a |
| `margin_balance_crowding_reversal_20` | 207 | 889830 | 4636 |
| `margin_financing_acceleration_exhaustion_20` | 207 | 889830 | 4636 |
| `shibor_liquidity_tightening_regime_20` | 205 | 205 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed improved to 4 primary observation dates, still below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` resolves with 198 observation dates, but HK hold primary feed still has only 4 observation dates. |

## Decision

Round182 improves canonical HK hold coverage from 3 to 4 primary observation dates and broadens the four matrix-ready seeds, but it does not change promotion status.

The correct interpretation remains:

- External margin, SHIBOR, and index-state seeds are matrix-ready.
- Northbound hold seeds are not matrix-ready because the primary holding feed is still too sparse.
- Join smoke is not alpha evidence.
- No cost/capacity walk-forward, redundancy audit, regime audit, or holdout audit was run.

Next controlled direction: continue monthly backfill with the next shard, `2025-02`, then run the Round181-183 three-round review after Round183 completes.
