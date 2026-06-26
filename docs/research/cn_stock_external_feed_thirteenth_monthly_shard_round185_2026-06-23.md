# CN Stock External Feed Thirteenth Monthly Shard - Round185

Date: 2026-06-23

## Scope

Round185 executed the 2024-12 monthly shard after Round184 added the HK hold and LPR coverage audit.

Shard:

- Start: `2024-12-01`
- End: `2024-12-31`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202412/external_feed_ingestion_report.json`
- Progress log: `data/reports/round185_external_feed_202412_shard_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Ingestion Result

Summary:

- Feed count: 5
- Pass: 4
- Warn: 1
- Fail: 0
- Progress events: 181

Feed details:

| Feed | Status | Rows | Notes |
| --- | --- | ---: | --- |
| `external_margin_detail` | pass | 71534 | Margin-detail shard wrote normally; `rqye` and `rzrqye` have 45 missing values. |
| `external_hk_hold` | pass | 3385 | CN-stock canonical output improved, but all valid rows are still on one sparse observation date in this shard. |
| `external_hsgt_flow` | pass | 13 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 22 | Index valuation and turnover fields are available; `close`, `pct_chg`, and `amount` are missing in this shard. |
| `external_macro_rates` | warn | 15 | SHIBOR present; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round185_external_feed_thirteen_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 3027744
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 265 | 265 | n/a |
| `margin_balance_crowding_reversal_20` | 255 | 1084632 | 4644 |
| `margin_financing_acceleration_exhaustion_20` | 255 | 1084632 | 4644 |
| `shibor_liquidity_tightening_regime_20` | 250 | 250 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed has only 5 observation dates, below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` reached 244 observation dates, but HK hold primary feed is still only 5 observation dates. |

## Post-Shard Coverage Audit

Report:

- `data/reports/round185_external_feed_hk_hold_lpr_coverage_audit_after_202412_shard_20260623/external_feed_coverage_audit.json`

Result:

- HK hold remains blocked: 5 observation dates, 17204 rows, 3950 symbols, 91.5-day median gap.
- LPR remains blocked: 250 macro rows, 250 complete SHIBOR rows, 0 LPR non-null rows.
- External-feed IC or portfolio work from blocked HK hold/LPR feeds remains disallowed.

## Decision

Round185 improves long-cycle coverage for margin, SHIBOR, index-state, and HSGT flow into 2024-12. It also confirms that HK hold is still a sparse low-frequency feed and LPR remains unusable.

Allowed next data-readiness path:

- Continue controlled backfill into 2024-11 for margin-detail, SHIBOR, and index-state long-cycle coverage.
- Keep HK hold out of daily ranking candidates until frequency/coverage is repaired or it is explicitly redesigned as a low-frequency state variable.
- Keep LPR out of all candidate definitions until non-missing coverage is repaired.

Blocked paths:

- No external-feed portfolio grid from matrix readiness alone.
- No profitability claim from join smoke.
- No daily northbound-hold ranking factor.
- No LPR factor.
