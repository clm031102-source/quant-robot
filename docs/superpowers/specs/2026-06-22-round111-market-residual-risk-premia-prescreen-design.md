# Round111 Market Residual Risk Premia Prescreen Design

## Goal

Run a long-cycle, same-parameter Alphalens-style prescreen for the 10 Round110 pre-registered CN stock market-residual risk-premia candidates.

## Scope

- Market: CN.
- Asset type: stock.
- Stage: statistical prescreen only.
- Default analysis window: 2015-01-01 through 2025-12-31.
- Final holdout: 2026 data is excluded by default and remains read-once only after later gates.

## Candidate Family

Round110 registered 10 candidates:

- `low_beta_120`
- `downside_beta_low_120`
- `idio_vol_low_60`
- `residual_reversal_5_60`
- `residual_momentum_quality_20_120`
- `low_market_corr_60`
- `crash_resilience_60`
- `beta_adjusted_range_contraction_60`
- `downside_residual_vol_low_60`
- `positive_residual_skew_60`

## Method

1. Load CN stock bars from the existing processed bars roots.
2. Build a same-date equal-weight market proxy from eligible CN stock daily returns.
3. For each stock, compute rolling market beta, downside beta, market correlation, residual returns, residual volatility, residual skew, co-crash counts, and beta-adjusted range features using only data available at the signal date.
4. Cross-sectionally z-score features per signal date only.
5. Materialize one factor matrix row per `(date, asset_id, factor_name)`.
6. Apply capacity/data filters before IC prescreen:
   - `amount >= min_signal_date_amount`
   - `adv20_amount >= min_signal_date_amount`
   - absolute daily return <= 50%
7. Build forward return labels with execution lag 1 through existing label helpers.
8. Summarize factor x horizon tests with Spearman IC, ICIR, t-stat, FDR, quantile spread, quantile monotonicity, and top-quantile turnover.
9. Keep promotion blocked. If research leads survive, the next allowed action is market exposure diagnostics and correlation dedup, not direct top-N portfolio promotion.

## Safety Rules

- No top-N portfolio grid in Round111.
- No parameter tuning after reading results.
- No final holdout read by default.
- No promotion from prescreen alone.
- No full-period normalization.
- No market proxy built from future returns.

