# CN Stock External Feed Sixteenth Monthly Shard - Round188

Date: 2026-06-23

## Scope

Round188 executed the 2024-09 monthly shard for the external macro, northbound, credit, and index-state feed pack.

Shard:

- Start: `2024-09-01`
- End: `2024-09-30`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202409/external_feed_ingestion_report.json`
- Progress log: `data/reports/round188_external_feed_202409_shard_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 4
- Warn: 1
- Fail: 0
- Progress events: 160

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 66683 | Margin-detail shard wrote normally; `rqye` and `rzrqye` have 53 missing values. |
| `external_hk_hold` | pass | 3540 | Canonical CN-stock output appears only on 2024-09-30; 11249 non-CN symbols were dropped. |
| `external_hsgt_flow` | pass | 17 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 19 | Index price and valuation/state fields are available for the shard. |
| `external_macro_rates` | warn | 18 | SHIBOR present after canonical processing; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round188_external_feed_sixteen_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 3586126
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 323 | 323 | n/a |
| `margin_balance_crowding_reversal_20` | 303 | 1275871 | 4649 |
| `margin_financing_acceleration_exhaustion_20` | 303 | 1275871 | 4649 |
| `shibor_liquidity_tightening_regime_20` | 295 | 295 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed has only 6 observation dates, below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` reached 290 observation dates, but HK hold primary feed is still only 6 observation dates. |

## Post-Shard Coverage Audit

Report:

- `data/reports/round188_external_feed_hk_hold_lpr_coverage_audit_after_202409_shard_20260623/external_feed_coverage_audit.json`

Result:

- HK hold remains blocked: 6 observation dates, 20744 rows, 3952 symbols, 92-day median gap.
- LPR remains blocked: 295 macro rows, 295 complete SHIBOR rows, 0 LPR non-null rows.
- External-feed IC or portfolio work from blocked HK hold/LPR feeds remains disallowed.

## Decision

Round188 improves long-cycle coverage for margin, SHIBOR, index-state, and HSGT flow into 2024-09. HK hold gained one additional low-frequency observation date, but remains far below daily ranking requirements.

Allowed next data-readiness path:

- Continue controlled backfill into 2024-08 for margin-detail, SHIBOR, and index-state long-cycle coverage.
- Keep HK hold out of daily ranking candidates until canonical CN-stock coverage is repaired or it is explicitly redesigned as a low-frequency state variable.
- Keep LPR out of all candidate definitions until non-missing coverage is repaired.

Blocked paths:

- No external-feed portfolio grid from matrix readiness alone.
- No profitability claim from join smoke.
- No daily northbound-hold ranking factor.
- No LPR factor.
