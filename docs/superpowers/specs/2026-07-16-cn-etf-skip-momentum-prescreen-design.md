# CN ETF Skip-Momentum Prescreen Design

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_batch`

Branch: `codex/factor-batch-cn-etf-price-rotation-20260716`

Base dependency: local integrity-remediation branch through commit `798bcd60`; this branch is intentionally stacked until laptop integration places that evidence on `main`.

## Objective

Test the only materially unexamined sub-hypothesis in the scheduler's `cn_etf_price_rotation` family: whether medium-horizon ETF momentum becomes more predictive when the most recent reversal-prone interval is excluded.

This stage may produce a statistical research lead only. It cannot create a portfolio candidate, paper signal, promotion claim, or live-trading path.

## Prior Evidence And Stop-Loss Review

The following CN ETF price-rotation paths are already closed under their existing structures:

- Plain `momentum_20` and `momentum_60`.
- `risk_adjusted_momentum_20` and `risk_adjusted_momentum_60`.
- `market_relative_strength_60` and its rank-equivalent dispersion transform.
- Liquidity-gated and maturity-filtered relative strength.
- Static-theme relative strength and theme-member leadership.
- Tail-guard reversal and the existing defensive reversal blend.

The repository explicitly says not to mutate those windows or loosen their gates. They remain reference exposures for duplicate detection, not candidates for another batch.

Repository search found no completed CN ETF test for a skip-window momentum factor. The CN stock information-discreteness study does include a skip-window signal, but its stock-level rejection does not answer the ETF-rotation hypothesis.

## Considered Approaches

### Reuse The Existing FIP Candidate Only

This is the smallest implementation, but it mixes skip momentum with path continuity and volatility. A result would not identify whether the skip construction or the quality overlay carried the signal.

### Compact Pure Skip-Momentum Batch With One Existing Diagnostic

This is the selected approach. It freezes two economically distinct skip intervals and includes the existing FIP candidate as a diagnostic benchmark. It isolates the hypothesis while limiting multiple testing to six factor-horizon tests.

### Stop The Family Immediately

This respects the large amount of negative momentum and reversal evidence, but it would close the scheduler's last untested price-rotation subspace without direct evidence. It is too conservative before one compact prescreen.

## Frozen Candidates

Higher values always mean a more bullish ETF rank.

| Factor | Formula At Signal Date `t` | Economic Interpretation |
| --- | --- | --- |
| `etf_skip5_momentum_60` | `adj_close[t-5] / adj_close[t-65] - 1` | Preserve the prior three-month trend while excluding the latest trading week, where ETF flow reversal and rebalance noise can dominate. |
| `etf_skip20_momentum_120` | `adj_close[t-20] / adj_close[t-140] - 1` | Preserve a medium-term trend while excluding the most recent trading month, analogous to a daily 12-minus-1 style rotation signal. |
| `fip_smooth_momentum_skip5_60` | Existing registered information-discreteness formula | Diagnostic only: tests whether path continuity and low volatility improve the same skip-five-day thesis. |

No additional windows, weights, signs, or formula variants may be added after observing results.

## Data And Point-In-Time Universe

Primary local root:

`data/processed/tushare_etf_wide_history_2023_2026`

Despite its name, the current processed coverage is 1,119,490 rows, 1,781 assets, and 1,085 sessions from 2020-01-02 through 2024-06-28. The prescreen must record this stale endpoint explicitly.

The static Round25 set of 264 ETFs must not define historical membership because it was selected using 2024 endpoint liquidity. Instead, each signal date uses a point-in-time eligibility mask:

1. Official `tushare_fund_basic.is_etf` is true.
2. Official `list_date` is on or before the signal date.
3. `delist_date` is absent or on or after the signal date.
4. At least 252 prior observed sessions exist for the asset.
5. Trailing 20-session median amount is at least CNY 5,000,000.
6. Trailing 20-session stale-price rate is at most 5%.
7. The current adjusted price and amount are positive.
8. The current absolute one-day adjusted return is at most 20%.

The signal-date cross-section must contain at least 30 eligible ETFs. Missing official metadata fails closed.

The analysis window is fixed to the available 2020-01-02 through 2024-06-28 data. The 2026 final holdout is prohibited. Any later walk-forward stage requires a separate 2024-H2 through 2025 history backfill and freshness audit before it starts.

## Labels And Statistical Tests

- Forward horizons: 5 and 20 sessions.
- Execution lag: 1 session.
- Rank metric: same-date Spearman IC.
- IC significance: Newey-West mean test with lag `horizon - 1`.
- Multiple testing: Benjamini-Hochberg FDR across all 3 factors x 2 horizons at alpha 0.05.
- Shape checks: top-minus-bottom quintile return, quintile monotonicity, and top-quintile turnover.
- Time checks: calendar-year IC rows, at least three usable years, and at least 60% of usable years with positive mean IC.

## Duplicate Gate

Each candidate is compared by same-date cross-sectional Spearman correlation against the already tested references:

- `momentum_20`
- `momentum_60`
- `risk_adjusted_momentum_20`
- `risk_adjusted_momentum_60`
- `reversal_5`
- `reversal_20`
- `market_relative_strength_20`
- `market_relative_strength_60`

A candidate is a hard duplicate when its maximum absolute mean daily correlation is at least 0.85. Rank-equivalent transforms are rejected even if their formula text differs.

## Research-Lead Gate

A factor-horizon row is a research lead only when every condition passes:

- FDR-adjusted significance at alpha 0.05.
- Mean Rank IC at least 0.02.
- ICIR at least 0.30.
- Positive daily IC rate at least 55%.
- Positive top-minus-bottom quintile return.
- Quintile monotonicity at least 0.70.
- Average top-quintile turnover at most 90%.
- At least three usable calendar years and at least 60% positive years.
- Maximum absolute reference correlation below 0.85.

These are discovery gates, not profitability claims.

## Decision Rules

If no row passes, close the remaining skip-momentum subspace and rotate the scheduler away from `cn_etf_price_rotation`; do not tune windows, thresholds, weights, or costs.

If one or more rows pass, freeze only the smallest non-duplicate lead set. Before any walk-forward run:

1. Backfill and audit 2024-H2 through 2025 CN ETF history.
2. Freeze a compact walk-forward config with 5/10/20 bps costs, capacity, turnover, and regime coverage.
3. Keep 2026 sealed.

## Components

- A focused ETF skip-momentum factor module for the two pure formulas.
- A duplicate/stop-loss evidence builder that records the closed historical paths.
- A point-in-time ETF universe loader using official fund metadata and trailing-only eligibility.
- A prescreen engine that computes labels, IC statistics, FDR, yearly stability, and duplicate correlations.
- A CLI that writes JSON, Markdown, and compact CSV evidence under ignored `data/reports`.
- Unit and CLI tests covering causality, lifecycle filtering, holdout exclusion, duplicate blocking, FDR gates, and no-portfolio safety.

## Safety

Research-to-paper only. No broker connection, account read, order placement, automatic live trading, or profitability claim is allowed.
