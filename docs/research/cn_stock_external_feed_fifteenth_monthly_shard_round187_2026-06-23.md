# CN Stock External Feed Fifteenth Monthly Shard - Round187

Date: 2026-06-23

## Scope

Round187 executed the 2024-10 monthly shard for the external macro, northbound, credit, and index-state feed pack.

Shard:

- Start: `2024-10-01`
- End: `2024-10-31`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202410/external_feed_ingestion_report.json`
- Progress log: `data/reports/round187_external_feed_202410_shard_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 3
- Warn: 2
- Fail: 0
- Progress events: 149

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 59141 | Margin-detail shard wrote normally; `rqye` and `rzrqye` have 38 missing values. |
| `external_hk_hold` | warn | 0 | Raw endpoint returned rows during progress, but canonical CN-stock output is empty; 11409 non-CN symbols were dropped. |
| `external_hsgt_flow` | pass | 10 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 18 | Index price and valuation/state fields are available for the 18 trading days in this holiday month. |
| `external_macro_rates` | warn | 14 | SHIBOR present after canonical processing; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round187_external_feed_fifteen_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 3275724
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 304 | 304 | n/a |
| `margin_balance_crowding_reversal_20` | 286 | 1208589 | 4647 |
| `margin_financing_acceleration_exhaustion_20` | 286 | 1208589 | 4647 |
| `shibor_liquidity_tightening_regime_20` | 277 | 277 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed remains at 5 observation dates, below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` reached 273 observation dates, but HK hold primary feed is still only 5 observation dates. |

## Post-Shard Coverage Audit

Report:

- `data/reports/round187_external_feed_hk_hold_lpr_coverage_audit_after_202410_shard_20260623/external_feed_coverage_audit.json`

Result:

- HK hold remains blocked: 5 observation dates, 17204 rows, 3950 symbols, 91.5-day median gap.
- LPR remains blocked: 277 macro rows, 277 complete SHIBOR rows, 0 LPR non-null rows.
- External-feed IC or portfolio work from blocked HK hold/LPR feeds remains disallowed.

## Decision

Round187 improves long-cycle coverage for margin, SHIBOR, index-state, and HSGT flow into 2024-10. It again confirms that HK hold raw endpoint rows are not enough because they do not survive canonical CN-stock filtering in this shard.

Allowed next data-readiness path:

- Continue controlled backfill into 2024-09 for margin-detail, SHIBOR, and index-state long-cycle coverage.
- Keep HK hold out of daily ranking candidates until canonical CN-stock coverage is repaired or it is explicitly redesigned as a low-frequency state variable.
- Keep LPR out of all candidate definitions until non-missing coverage is repaired.

Blocked paths:

- No external-feed portfolio grid from matrix readiness alone.
- No profitability claim from join smoke.
- No daily northbound-hold ranking factor.
- No LPR factor.
