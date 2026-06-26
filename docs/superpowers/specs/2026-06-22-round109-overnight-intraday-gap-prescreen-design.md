# Round109 Overnight-Intraday Gap Prescreen Design

## Context

Round108 hibernated the `overheat_avoidance_relative_strength_60` line because the lead was highly redundant with hard-blocking capacity-safe price-volume references. The next run must rotate family rather than tune the same trend/amount source.

Round109 uses an OHLC-only public-reference family: overnight return, open-to-close intraday return, and gap-fill behavior. The data already contains `open`, `close`, `adj_close`, `amount`, and `volume`, so no new Tushare download or financial PIT backfill is required.

## Public Reference Basis

- Alphalens-style evaluation: IC, quantile spread, turnover, and multiple-testing accounting before any portfolio grid.
- Qlib Alpha158/Alpha360-style discipline: fixed feature formulas, explicit windows, and no post-hoc parameter search.
- Academic/public anomaly family: separate overnight return from intraday/open-to-close return and test whether one component contains different predictive information from the other.

## Candidate Family

The family is `overnight_intraday_gap`. All factors are higher-is-better and use only same-day or earlier OHLCV data. Execution must lag at least one trading day because close-derived signals are used.

Pre-registered candidates:

| Factor | Formula Intuition | Windows |
|---|---|---|
| `overnight_reversal_5` | Buy stocks with weak recent overnight returns, expecting overnight overreaction to mean-revert. | 5 |
| `overnight_reversal_20` | Longer version of overnight overreaction reversal. | 20 |
| `intraday_momentum_5` | Buy stocks with persistent open-to-close strength. | 5 |
| `intraday_momentum_20` | Longer version of intraday strength. | 20 |
| `gap_down_intraday_recovery_10` | Buy gap-down stocks that recover during the trading day. | 10 |
| `gap_up_intraday_fade_10` | Test whether gap-up stocks sold intraday contain contrarian information. | 10 |
| `gap_fill_efficiency_20` | Reward days where intraday movement fills the overnight gap rather than extends it. | 20 |
| `overnight_intraday_disagreement_20` | Reward negative rolling correlation between overnight and intraday returns. | 20 |
| `gap_extreme_avoidance_20` | Prefer liquid stocks without repeated extreme overnight gaps. | 20 |
| `gap_reversal_lowvol_liquid_20` | Combine overnight reversal, lower realized volatility, and liquidity quality. | 20 |

## Data And Gates

- Market: CN stock only.
- Data window: default 2015-01-01 through 2025-12-31.
- Final holdout: not included.
- Capacity filters: `amount >= 10,000,000` and `adv20_amount >= 10,000,000`.
- Minimum cross-section: 30 names per signal date.
- Horizons: 5 and 20 trading days.
- Multiple testing: Bonferroni and FDR both recorded; research leads require FDR significance.
- Promotion: always false in this stage. A lead can only move to dedup or cost/capacity bridge after prescreen.

## Expected Outputs

- JSON report: `overnight_intraday_gap_prescreen.json`.
- Markdown report: `overnight_intraday_gap_prescreen.md`.
- Candidate CSV: `overnight_intraday_gap_candidates.csv`.
- Results CSV: `overnight_intraday_gap_results.csv`.
- IC observations CSV: `overnight_intraday_gap_ic_observations.csv`.

## Decision Rules

If one or more research leads pass IC, quantile monotonicity, turnover, and FDR gates, next direction is `round110_overnight_intraday_gap_lead_dedup`. If none pass, next direction is `round110_family_rotation_after_overnight_intraday_gap_failure`.

This run does not allow top-N portfolio grids, parameter tuning, paper-ready claims, or live/manual trading claims.
