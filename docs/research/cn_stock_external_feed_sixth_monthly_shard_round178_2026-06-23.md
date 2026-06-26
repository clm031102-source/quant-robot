# CN Stock External Feed Sixth Monthly Shard - Round178

Date: 2026-06-23

## Scope

Round178 continued the controlled long-cycle external-feed backfill for CN stock factor mining.

Shard:

- Start: `2025-07-01`
- End: `2025-07-31`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202507/external_feed_ingestion_report.json`
- Progress log: `data/reports/round178_external_feed_sixth_monthly_shard_202507_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 3
- Warn: 2
- Fail: 0
- Progress events: 189
- Stderr: empty

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 95087 | 4177 entities, no lag violations, no duplicate keys. |
| `external_hsgt_flow` | pass | 22 | Available dates from 2025-07-03 to 2025-08-01. |
| `external_index_state` | pass | 23 | One index entity, no PIT lag violations. |
| `external_macro_rates` | warn | 23 | SHIBOR present; LPR still missing or rate-limited. |
| `external_hk_hold` | warn | 0 | Final CN-filtered feed is empty for this shard. Raw endpoint progress showed rows, but the canonical quality report remains the source of truth. |

## Cumulative Join Smoke

Report:

- `data/reports/round178_external_feed_six_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 1294595
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 126 | 126 | n/a |
| `margin_balance_crowding_reversal_20` | 126 | 548525 | 4582 |
| `margin_financing_acceleration_exhaustion_20` | 126 | 548525 | 4582 |
| `shibor_liquidity_tightening_regime_20` | 125 | 125 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed still has only 2 primary observation dates. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` resolves with 120 observation dates, but HK hold primary feed still has only 2 primary observation dates. |

## Quality-Gate Update

The CN stock quality gate evidence was updated from Round177 to Round178 for China market regime controls:

- SHIBOR liquidity regime: 125 observation dates, still no LPR evidence.
- Credit-cycle/margin proxy: 126 observation dates, 548525 joined rows, 4582 symbols.
- Northbound temperature: HSGT flow is usable as secondary daily state, but HK hold remains blocked by low primary observation frequency.
- Index-location state: 126 observation dates.

Latest generated gates:

- `data/reports/round178_quality_gate_after_external_feed_shard_20260623/factor_mining_quality_gate.json`
- `data/reports/round178_startup_gate_after_external_feed_shard_20260623/factor_mining_startup_gate.json`

## Decision

Round178 improves long-cycle external-feed coverage and keeps PIT joins clean.

It does not produce a promotable factor:

- Join smoke is not IC evidence.
- No cost/capacity walk-forward was run.
- No redundancy, regime, or final-holdout audit was run.
- HK hold based northbound factors remain blocked.

Next controlled direction: continue monthly backfill with the next shard while preserving the quality-gate evidence/action ledger.
