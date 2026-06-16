# Office Desktop Incremental Factor Mining - 2026-06-16

## Scope

- Machine role: `office_desktop`.
- Branch: `codex/factor-batch-moneyflow-alpha`.
- Task type: `factor_batch` with follow-up validation.
- Research boundary: research-to-paper only. No broker connection, no live account reads, no order placement, and no automatic live trading.
- Data policy: raw data, processed data, generated reports, logs, and local credentials remain out of Git.

## Data Refresh

The local Tushare provider smoke passed for `daily`, `daily_basic`, and `moneyflow` on 2026-06-10 through 2026-06-12. The incremental research dataset then refreshed CN daily bars and moneyflow inputs from 2025-07-01 through 2026-06-15.

Daily bars:

- Rows: 1,264,720.
- Assets: 5,550.
- Duplicate bars: 0.
- Zero-volume rows: 0.
- Missing date rows: 2,359.
- Stale price rows: 4,233.
- Extreme return rows: 13.
- Adjusted-close jump rows: 3.

Moneyflow inputs:

- Rows: 1,192,766.
- Assets: 5,228.
- Duplicate rows: 0.
- Missing asset-id rows: 0.
- Missing numeric rows: 0.

Daily data quality is good enough for research screening but not clean enough for promotion without a data-quality penalty and reviewer inspection of stale prices, missing dates, extreme returns, and adjusted-close jumps.

## Candidate Mining Results

The first incremental priority check retested prior observation candidates on 2025-07-01 through 2026-06-15:

- `mf_low_plus_reversal_5`: rejected. IC was not significant, total return was negative, and drawdown exceeded the configured limit.
- `small_sell_plus_reversal_5`: rejected. IC was not significant, total return was negative, and drawdown exceeded the configured limit.
- `mf_low_minus_volatility_20`: observation only. Backtest return was strong, but IC was not significant, long-short spread was negative, and two trades breached the capacity limit.
- `large_minus_liquidity_20`: promoted to strict-validation candidate. Full incremental top5/cost20 had significant positive IC, positive relative return, acceptable drawdown, and no capacity-limited trades.

## `large_minus_liquidity_20` Evidence

Formula family: large-order net inflow z-score minus 20-day Amihud-style illiquidity z-score.

Full incremental run, top5, 20 bps:

- Total return: 2.0249.
- Relative return: 1.8284.
- Sharpe: 2.7649.
- Max drawdown: -0.1749.
- Mean IC: 0.02037.
- IC p-value: 5.94e-10.
- Positive IC rate: 68.4%.
- Long-short mean return: 0.00050.
- Long-short positive rate: 57.5%.
- Capacity-limited trades: 0.

Half-year robustness:

- 2025H2 top5/cost20: total return 0.7520, Sharpe 2.6710, max drawdown -0.1677, capacity-limited trades 0.
- 2026H1 top5/cost20: total return 0.5467, Sharpe 2.4413, max drawdown -0.1749, capacity-limited trades 0.
- Top10/cost20 also passed in both half-year windows.
- Top20/cost30 failed, so the signal is not broad-capacity evidence.

Rolling walk-forward, top5, 20 bps:

- Folds: 2.
- Accepted folds: 2.
- Mean test relative return: 0.2735.
- Mean test Sharpe: 3.5586.
- Worst test drawdown: -0.1749.
- Test mean IC: 0.02280.
- Test IC p-value: 0.00377.
- Test positive IC rate: 65.0%.
- Test capacity-limited trades: 0.

## Audit Judgment

`large_minus_liquidity_20` is useful enough to keep in the strict walk-forward candidate set and push as a lightweight research finding. It is not approved for live trading or automatic paper promotion.

Reasons to keep auditing:

- RankIC was negative in the full and 2025H2 checks, and not significant in 2026H1. This means the edge may be tail-driven rather than smoothly monotonic.
- Top20/cost30 failed, so capacity breadth is limited.
- Daily data quality has stale price, missing-date, extreme-return, and adjusted-close jump issues.
- The rolling validation has only two folds on the incremental window.

Next steps:

1. Re-run strict rolling validation with longer combined 2023-2026 coverage after merging archive and incremental stores.
2. Add market-cap, industry, and liquidity neutralization before any promotion decision.
3. Inspect quantile monotonicity and tail dependence because RankIC does not confirm the Pearson IC story.
4. Keep `large_minus_liquidity_20` in `configs/walk_forward_tushare_moneyflow_technical_combo.json` for future validation runs.
