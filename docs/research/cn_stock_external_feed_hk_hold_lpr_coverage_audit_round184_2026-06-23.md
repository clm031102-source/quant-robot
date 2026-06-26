# CN Stock External Feed HK Hold and LPR Coverage Audit - Round184

Date: 2026-06-23

## Scope

Round184 added a reusable coverage audit before any external-feed IC screen or portfolio grid.

Audited source:

- Processed root: `data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Audit report: `data/reports/round184_external_feed_hk_hold_lpr_coverage_audit_20260623/external_feed_coverage_audit.json`
- Audit markdown: `data/reports/round184_external_feed_hk_hold_lpr_coverage_audit_20260623/external_feed_coverage_audit.md`

This is a coverage and control audit. It is not IC evidence, portfolio evidence, or profitability evidence.

## Audit Result

Summary:

- Audited feeds: 2
- Pass: 0
- Blocked: 2
- External-feed IC or portfolio work allowed from these blocked feeds: false

## HK Hold Coverage

`external_hk_hold` remains blocked for daily stock ranking.

| Metric | Value |
| --- | ---: |
| Rows | 13819 |
| Unique observation dates | 4 |
| First date | 2025-03-31 |
| Last date | 2025-12-31 |
| Unique symbols | 3945 |
| Median gap days | 92 |
| Max gap days | 92 |
| Detected frequency | quarterly_or_sparse |
| Missing `hold_ratio` | 0 |
| Missing `hold_vol` | 0 |

Blockers:

- `hk_hold_observation_dates_below_minimum`
- `hk_hold_frequency_not_daily_enough_for_daily_rank`

Blocked uses:

- `external_feed_hk_hold_daily_rank_factor_before_frequency_repair`
- `northbound_hold_ratio_accumulation_before_hk_hold_coverage_repair`
- `northbound_hold_accumulation_flow_regime_before_hk_hold_coverage_repair`

Decision: do not use HK hold as a daily cross-sectional A-share rank factor. If retained, redesign it as a low-frequency state or interaction variable and re-audit the frequency first.

## Macro LPR Coverage

`external_macro_rates` has complete SHIBOR coverage for the current processed window, but LPR is unusable.

| Metric | Value |
| --- | ---: |
| Rows | 222 |
| Unique observation dates | 222 |
| First date | 2025-02-05 |
| Last date | 2025-12-31 |
| SHIBOR complete rows | 222 |
| LPR 1Y non-null rows | 0 |
| LPR 5Y non-null rows | 0 |
| LPR complete rows | 0 |
| LPR non-null ratio | 0.00% |

Blocker:

- `lpr_non_missing_coverage_below_threshold`

Blocked uses:

- `external_feed_lpr_factor_before_non_missing_lpr_coverage`
- `policy_liquidity_lpr_regime_before_lpr_coverage_repair`

Decision: keep SHIBOR as a possible market liquidity regime-control seed, but keep every LPR-dependent factor blocked until non-missing LPR coverage is repaired.

## Next Direction

Proceed with the 2025-01 monthly shard only for the feeds that still improve usable coverage:

- margin-detail credit seeds
- SHIBOR liquidity regime seed
- index-state regime seed

Do not run external-feed IC or portfolio grids from HK hold or LPR. Do not promote any external-feed result until long-cycle coverage, PIT joins, IC/quantile/turnover, neutralization, redundancy, regime coverage, cost/capacity, walk-forward, and holdout gates are all available.
