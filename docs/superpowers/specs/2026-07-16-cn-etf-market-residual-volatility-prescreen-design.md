# CN ETF Market-Residual Volatility Prescreen Design

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_review`, followed by a separate `factor_batch` branch for implementation

Review branch: `codex/factor-review-cn-etf-volatility-regime-20260716`

## Objective

Run one compact, previously untested CN ETF prescreen for market-residual volatility and tail shape. The batch must determine whether the residual subspace contains a statistically credible, non-duplicate, capacity-feasible research lead after the raw volatility, downside-volatility, drawdown, recovery, compression, and regime branches have been closed.

This stage can produce only a research lead. It cannot authorize a portfolio grid, walk-forward run, paper signal, promotion, broker access, account read, order placement, or live trading.

## Historical Boundary

The following structures are references and cannot be resubmitted as candidates:

- Raw `volatility_5/10/20/60/120`.
- `low_volatility_20/60` and `low_downside_volatility_60`.
- `drawdown_resilience_60`, crash/recovery factors, and defensive blends.
- State-adaptive defense and stress-only factors.
- Hard positive-momentum regime filters.
- Range-contraction, low-volatility/liquidity range variants, Bollinger, and SuperTrend/ATR structures.

No candidate may add a liquidity reward to improve capacity optics. Capacity is a separate hard gate.

## Point-In-Time Market Proxy

For each date `t`, calculate `market_return[t]` as the median one-session adjusted return across ETFs that pass the official point-in-time eligibility policy on `t`.

- Membership must use only information available on `t`.
- The static Round25 endpoint universe is prohibited.
- A date requires at least 30 eligible ETF returns.
- The median is frozen to reduce sensitivity to extreme ETF returns; mean/benchmark substitutions are not allowed after results.

## Frozen Candidates

Higher values always indicate a more favorable ETF rank.

### `etf_idio_vol_low_60`

Estimate rolling market beta with 120 sessions and at least 80 valid return pairs. Estimate alpha from the same rolling window. Shift alpha and beta by one session before computing the current residual:

`residual[t] = return[t] - alpha[t-1] - beta[t-1] * market_return[t]`

The factor is negative 60-session residual standard deviation with at least 40 valid residuals:

`factor[t] = -std(residual[t-59:t])`

Hypothesis: lower ETF-specific noise after common-market removal proxies tracking quality and stable demand rather than merely low broad-market exposure.

### `etf_downside_beta_low_120`

On sessions where `market_return < 0`, estimate rolling 120-session beta with at least 24 negative-market observations:

`downside_beta = cov(return, market_return) / var(market_return)`

`factor[t] = -downside_beta[t]`

Hypothesis: ETFs with lower sensitivity specifically on market-down sessions preserve capital and rank better than raw low-volatility ETFs.

### `etf_positive_residual_skew_60`

Use the same one-session-lagged 120-session alpha/beta residual as `etf_idio_vol_low_60`. Calculate 60-session residual skew with at least 40 residuals:

`factor[t] = skew(residual[t-59:t])`

Hypothesis: favorable asset-specific upside-tail shape is distinct from low residual volatility and raw drawdown resilience.

No alternate beta windows, residual windows, minimum observations, signs, transforms, combinations, or weights may be introduced after observing results.

## Historical Reference Gate

Each candidate must be compared by same-date cross-sectional Spearman correlation with these already tested exposures:

- `low_volatility_20`
- `low_volatility_60`
- `low_downside_volatility_60`
- `drawdown_resilience_60`
- `crash_recovery_60`
- `recovery_quality_60`
- `formula_range_contraction_breakout_20`
- `formula_range_contraction_breakout_lowvol_20`
- `bollinger_reversal_20`

A candidate is a hard duplicate when its maximum absolute mean daily Spearman correlation is at least 0.85. Missing reference evidence fails closed. The reference list cannot be shortened after results.

## Data And Eligibility

Primary local root: `data/processed/tushare_etf_wide_history_2023_2026`.

The actual source window is 2020-01-02 through 2024-06-28. The directory name does not authorize reading later data. The 2026 final holdout is sealed. Any later walk-forward requires an audited 2024-H2 through 2025 backfill first.

The loader must skip partitions after the configured analysis year before opening their files. Filtering 2026 rows only after loading is not considered a sealed holdout.

Signal-date eligibility requires:

- Official ETF flag and valid list/delist lifecycle.
- At least 252 prior observations.
- Trailing 20-session median amount of at least CNY 5 million.
- Trailing 20-session stale-price rate no greater than 5%.
- Positive current adjusted price and amount.
- Absolute current adjusted return no greater than 20%.

## Statistical Gate

- Forward horizons: 5 and 20 sessions.
- Execution lag: 1 session.
- Daily test: same-date Spearman Rank IC.
- Dependence correction: Newey-West mean test with lag `horizon - 1`.
- Multiple testing: Benjamini-Hochberg FDR across all 3 x 2 frozen tests at alpha 0.05.
- Mean Rank IC at least 0.02.
- ICIR at least 0.30.
- Positive daily IC rate at least 55%.
- Positive top-minus-bottom quintile return.
- Quintile monotonicity at least 0.70.
- Average top-quintile turnover no greater than 90%.
- At least three usable calendar years and at least 60% positive years.
- Maximum absolute historical-reference correlation below 0.85.

## Capacity Gate

Use signal-date trailing 20-session mean CNY amount. For every factor-horizon row, evaluate ADV20 across all valid top-quintile asset-dates.

Frozen assumption:

- Portfolio value: CNY 1,000,000.
- Equal positions: 10.
- One-way notional per position: CNY 100,000.
- Maximum one-way participation: 1%.
- Required tenth-percentile top-quintile ADV20: CNY 10 million.
- Required capacity evidence coverage: 100%.

Missing or insufficient capacity evidence fails closed.

## Decision Rules

If at least one factor-horizon row passes every statistical, yearly-stability, duplicate, and capacity gate:

1. Freeze the smallest passing factor set and artifact hashes.
2. Keep `cn_etf_volatility_regime` active only for that frozen lead.
3. Backfill and audit 2024-H2 through 2025 before designing a walk-forward.
4. Do not run a portfolio grid or claim profitability from the prescreen.

If no row passes:

1. Stop-loss `cn_etf_volatility_regime` at budget 0.
2. Keep flow breadth at 0.35 and raise fund structure to 0.35.
3. Activate `cn_etf_peer_relative_value` at 0.30.
4. Require a metadata-readiness review and separate preregistration before any peer-relative factor implementation.
5. Prohibit all residual-volatility sign, window, threshold, regime, portfolio, and walk-forward rescue.

## Required Implementation

- A dedicated ETF residual-risk factor module with formula and causality tests.
- A thin prescreen wrapper using the shared cross-sectional statistical engine.
- Historical-reference computation that requests only the frozen names.
- Historical-reference completeness that fails closed when a frozen reference lacks the minimum usable daily cross-sections.
- Capacity diagnostics with fail-closed evidence coverage.
- A config-driven CLI that rejects 2026 dates and any drift in the frozen analysis window, eligibility policy, market proxy, candidate parameters, factor/reference names, thresholds, capacity assumptions, multiple-testing policy, zero-lead allocation, or execution boundaries.
- JSON, Markdown, result, IC, yearly IC, reference-correlation, and capacity artifacts under ignored `data/reports/` paths.

## Safety

Research-to-paper only. No broker connection, live account read, order placement, automatic live trading, paper signal, or profitability claim is allowed.
