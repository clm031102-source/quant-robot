# CN Stock External Feed Twelfth Monthly Shard - Round184

Date: 2026-06-23

## Scope

Round184 executed the 2025-01 monthly shard after adding the HK hold and LPR coverage audit.

Shard:

- Start: `2025-01-01`
- End: `2025-01-31`
- Output root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Shard report: `data/reports/round172_external_feed_long_cycle_backfill_shard_reports_20260623/shard_202501/external_feed_ingestion_report.json`
- Progress log: `data/reports/round184_external_feed_twelfth_monthly_shard_202501_20260623/progress.jsonl`

This is data and factor-matrix readiness work. It is not IC evidence and not profitability evidence.

## Pre-Shard Coverage Audit

Before running the shard, Round184 added `external_feed_coverage_audit`:

- Report: `data/reports/round184_external_feed_hk_hold_lpr_coverage_audit_20260623/external_feed_coverage_audit.json`
- HK hold blocker: 4 observation dates, 92-day median gap, quarterly/sparse frequency.
- LPR blocker: 0 non-null rows across `lpr_1y` and `lpr_5y`.

The audit made the direction explicit: keep HK hold daily ranking and LPR-dependent factors blocked.

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
| `external_margin_detail` | pass | 52257 | Margin-detail shard wrote normally; `rqye` and `rzrqye` have 43 missing values. |
| `external_hk_hold` | warn | 0 | Canonical CN-stock output is empty; 12227 non-CN symbols were dropped. |
| `external_hsgt_flow` | pass | 16 | Northbound flow rows available for the shard. |
| `external_index_state` | pass | 18 | Index-state rows available for the shard. |
| `external_macro_rates` | warn | 13 | SHIBOR present; LPR still missing or rate-limited. |

## Cumulative Join Smoke

Report:

- `data/reports/round184_external_feed_twelve_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 2694712
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

History-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 243 | 243 | n/a |
| `margin_balance_crowding_reversal_20` | 237 | 1013098 | 4644 |
| `margin_financing_acceleration_exhaustion_20` | 237 | 1013098 | 4644 |
| `shibor_liquidity_tightening_regime_20` | 235 | 235 | n/a |

Still blocked:

| Seed | Status | Reason |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | insufficient_history | HK hold primary feed remains at 4 observation dates, below the 25-day minimum. |
| `northbound_hold_accumulation_flow_regime_20` | insufficient_history | Secondary `north_money` increased to 231 observation dates, but HK hold primary feed is still only 4 observation dates. |

## Post-Shard Coverage Audit

Report:

- `data/reports/round184_external_feed_hk_hold_lpr_coverage_audit_after_202501_shard_20260623/external_feed_coverage_audit.json`

Result:

- HK hold remains blocked: 4 observation dates, 13819 rows, 3945 symbols, 92-day median gap.
- LPR remains blocked: 235 macro rows, 235 complete SHIBOR rows, 0 LPR non-null rows.
- External-feed IC or portfolio work from blocked HK hold/LPR feeds remains disallowed.

## Decision

Round184 improves margin, SHIBOR, index-state, and HSGT coverage at the start of 2025, while confirming that HK hold and LPR are still not usable factor inputs.

Allowed next data-readiness path:

- Continue controlled backfill into 2024-12 for margin-detail, SHIBOR, and index-state long-cycle coverage.
- Keep HK hold out of daily ranking candidates until frequency/coverage is repaired.
- Keep LPR out of all candidate definitions until non-missing coverage is repaired.

Blocked paths:

- No external-feed portfolio grid from one year of data.
- No profitability claim from matrix-ready seeds.
- No daily northbound-hold ranking factor.
- No LPR factor.
