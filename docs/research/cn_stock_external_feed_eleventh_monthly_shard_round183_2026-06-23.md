# CN Stock External Feed Eleventh Monthly Shard - Round183

Date: 2026-06-23

## Scope

Round183 continued controlled long-cycle external-feed backfill for CN stock factor mining.

Shard:

- Start: `2025-02-01`
- End: `2025-02-28`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202502/external_feed_ingestion_report.json`
- Progress log: `data/reports/round183_external_feed_eleventh_monthly_shard_202502_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 3
- Warn: 2
- Fail: 0
- Progress events: 149
- Stderr: empty

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 68978 | Margin-detail shard wrote normally despite one raw progress day with 0 rows. |
| `external_hk_hold` | warn | 0 | Formal canonical CN-stock output is empty for this shard. |
| `external_hsgt_flow` | pass | 17 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 18 | Index-state rows available for the shard. |
| `external_macro_rates` | warn | 17 | SHIBOR present; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round183_external_feed_eleven_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 2586963
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 225 | 225 | n/a |
| `margin_balance_crowding_reversal_20` | 224 | 959239 | 4638 |
| `margin_financing_acceleration_exhaustion_20` | 224 | 959239 | 4638 |
| `shibor_liquidity_tightening_regime_20` | 222 | 222 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed remains at 4 primary observation dates, still below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` resolves with 215 observation dates, but HK hold primary feed still has only 4 observation dates. |

## Decision

Round183 increases margin, SHIBOR, and index-state coverage but does not improve HK hold primary frequency and does not change promotion status.

The correct interpretation remains:

- External margin, SHIBOR, and index-state seeds are matrix-ready.
- Northbound hold seeds are not matrix-ready because the primary holding feed is still too sparse.
- Join smoke is not alpha evidence.
- No cost/capacity walk-forward, redundancy audit, regime audit, or holdout audit was run.

Next controlled action: run the Round181-183 three-round review before continuing external-feed mining.
