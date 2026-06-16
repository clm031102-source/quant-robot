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

## Continued Mining Notes

After the first strict-validation candidate was pushed, the office desktop continued mining the remaining pre-registered combo family on the same incremental dataset.

Observation-only rows:

- `large_plus_risk_momentum_10`: very strong backtest returns, but not promoted. The full incremental run had 10 capacity-limited trades, RankIC was significantly negative, and the 2026H1 split did not have significant IC.
- `extra_plus_momentum_10`: significant positive IC and strong backtest returns, but not promoted. RankIC was significantly negative and capacity-limited trades were present.
- `large_plus_momentum_5`: strong backtest returns, but not promoted. IC was not significant, RankIC was significantly negative, and capacity-limited trades were present.
- `mf_low_plus_momentum_5`: strong backtest returns and no capacity-limited trades, but not promoted. IC was not significant, RankIC was significantly negative, and the long-short spread was negative.

Rejected rows:

- `extra_low_plus_reversal_5`: negative return, weak IC, drawdown above limit, and capacity pressure.
- `small_sell_low_plus_momentum_5`: negative return, negative IC, drawdown above limit, and capacity pressure.

The continued run reinforces the current promotion rule: high Sharpe alone is not enough. A candidate must survive significance, monotonicity or tail-dependence review, cost, capacity, split-window robustness, and rolling walk-forward checks before it can move beyond observation.

## Combined Long-Sample Recheck

The archive replay store and the 2025-07-01 to 2026-06-15 incremental refresh were combined into a local research store covering 2023-07-03 through 2026-06-15:

- Daily bars: 3,806,375 rows, 5,634 assets, duplicate keys 0.
- Moneyflow inputs: 3,606,228 rows, 5,312 assets, duplicate keys 0.

`large_minus_liquidity_20` was rerun on the combined 2023-2026 sample at top5/cost20:

- Status: completed, but decision rejected.
- Rejection reason: drawdown above limit.
- Total return: 74.6567.
- Relative return: 61.3001.
- Sharpe: 0.8881.
- Max drawdown: -0.6159.
- Mean IC: 0.01464.
- IC p-value: 5.20e-12.
- Positive IC rate: 62.7%.
- Long-short mean return: 0.00488.
- Capacity-limited trades: 2.
- Max participation rate: 14.4%.

This long-sample result weakens the candidate. The signal still deserves strict validation because IC and spread evidence persist, but it is not promotion-ready: drawdown, capacity pressure, and negative RankIC remain unresolved.

Additional combined width/cost audit on `large_minus_liquidity_20`:

- Top10/cost20: rejected for drawdown above limit; max drawdown -0.6136 and capacity-limited trades 2.
- Top10/cost30: rejected for relative return below threshold and drawdown above limit.
- Top20/cost20: rejected for relative return below threshold and drawdown above limit; capacity-limited trades 0, but max drawdown -0.7042.
- Top20/cost30: rejected for relative return below threshold and drawdown above limit.

The wider portfolios reduce participation pressure but do not solve the drawdown and cost sensitivity problem. Current status is strict-validation observation, not promotion.

## Continued Combined Audits

The office desktop then tested whether existing controls could rescue the long-sample `large_minus_liquidity_20` shape without adding new factor code.

Regime filter, 20-day equal-weight market momentum, combined 2023-2026:

- Top5/cost20: rejected for drawdown above limit. Total return 59.3310, relative return 45.9744, Sharpe 1.1607, max drawdown -0.4185, capacity-limited trades 9, max participation 48.6%.
- Top10/cost20: rejected for drawdown above limit. Total return 33.2598, relative return 19.9032, Sharpe 1.0342, max drawdown -0.4026, capacity-limited trades 4, max participation 24.3%.
- Top20/cost20: rejected for relative return below threshold and drawdown above limit. Total return 12.8595, relative return -0.4971, Sharpe 0.9377, max drawdown -0.3871, capacity-limited trades 2, max participation 12.2%.

Weekly rebalance checks:

- Regime-filtered top20/cost20/rebalance5 reduced drawdown to -0.0906 and removed capacity-limited trades, but total return was only 0.3706 versus a 13.3566 equal-weight benchmark return, so it failed relative-return review.
- Unfiltered top20/cost20/rebalance5 had drawdown -0.2438 but total return only 0.0179, relative return -13.3387, and 4 capacity-limited trades.

The conclusion is that simple market-regime and weekly-rebalance controls reduce risk by cutting exposure, not by preserving a durable long-sample edge. `large_minus_liquidity_20` remains observation only.

Raw moneyflow priority factors were also checked on the combined store at top20/cost20:

- `large_order_net_amount_ratio`: significant positive IC, but rejected for relative return below threshold, drawdown -0.6577, 90 capacity-limited trades, and max participation above 500%.
- `extra_large_order_net_amount_ratio`: significant positive IC, but rejected for relative return below threshold, drawdown -0.7766, 34 capacity-limited trades, and max participation above 200%.
- `small_order_sell_pressure`: significant positive IC, but rejected for relative return below threshold, drawdown -0.6470, 78 capacity-limited trades, and max participation above 600%.
- `net_mf_amount_ratio_low`: significant positive IC and positive relative return, but rejected for drawdown -0.6382, 98 capacity-limited trades, max participation above 600%, and negative top-minus-bottom quantile spread.

`mf_low_minus_volatility_20` was then tested on the combined store at top10/top20/cost20:

- Top10/cost20: significant positive IC and RankIC, total return 147.5315, relative return 134.1749, but rejected for drawdown -0.3400, 183 capacity-limited trades, max participation above 250%, and negative long-short spread.
- Top20/cost20: significant positive IC and RankIC, total return 16.6587, relative return 3.3021, but rejected for drawdown -0.5481, 83 capacity-limited trades, max participation above 500%, and negative long-short spread.

These checks narrow the next useful direction: plain moneyflow strength and low-flow volatility variants have signal, but they are not tradable at the current 1,000,000 portfolio value without stronger liquidity gating and risk controls. The next factor-mining branch should pre-register liquidity-gated moneyflow-risk blends rather than keep widening raw top-N portfolios.

## Micro-Capacity Sensitivity

The next audit reduced portfolio value from 1,000,000 to 100,000 and widened the portfolios to top50/top100/top250. The goal was to test whether the rejected moneyflow signals were blocked only by sizing, or whether the ranking shape itself failed when capacity pressure was reduced.

`mf_low_minus_volatility_20`, combined 2023-2026, 100,000 portfolio value, cost20:

- Top50: rejected for relative return below threshold and drawdown above limit. Total return 4.0011, relative return -9.3554, Sharpe 0.5898, max drawdown -0.6566, capacity-limited trades 5, max participation 26.2%.
- Top100: rejected for relative return below threshold and drawdown above limit. Total return 0.6832, relative return -12.6734, Sharpe 0.4773, max drawdown -0.6998, capacity-limited trades 2, max participation 13.1%.
- Top250: rejected for relative return below threshold and drawdown above limit. Total return -0.2655, relative return -13.6221, Sharpe 0.3606, max drawdown -0.7678, capacity-limited trades 1, max participation 5.23%.

`net_mf_amount_ratio_low`, combined 2023-2026, 100,000 portfolio value, cost20:

- Top50: rejected for relative return below threshold and drawdown above limit. Total return 1.4843, relative return -11.8722, Sharpe 0.5055, max drawdown -0.7160, capacity-limited trades 5, max participation 26.2%.
- Top100: rejected for relative return below threshold and drawdown above limit. Total return 0.2086, relative return -13.1480, Sharpe 0.4236, max drawdown -0.7448, capacity-limited trades 2, max participation 13.1%.
- Top250: rejected for relative return below threshold and drawdown above limit. Total return -0.4090, relative return -13.7656, Sharpe 0.3324, max drawdown -0.8097, capacity-limited trades 1, max participation 5.23%.

This sensitivity check rejects the simple "just reduce capital or widen holdings" explanation. Capacity pressure falls roughly as expected, but the edge disappears or inverts before the strategy becomes capacity-clean. The next useful experiment should add explicit liquidity gates or residualization before selection; broader raw top-N portfolios are not a productive path.

## Technical Baseline Control

To avoid overfitting only inside the moneyflow family, the office desktop also ran a same-sample technical baseline on the combined 2023-2026 store with top20/cost20/1,000,000 portfolio value.

- `risk_adjusted_momentum_20`: rejected for relative return below threshold and drawdown above limit. Total return -0.8556, relative return -14.2121, Sharpe 0.1589, max drawdown -0.9800, IC not significant, capacity-limited trades 4.
- `liquidity_20`: rejected for relative return below threshold and drawdown above limit. Total return -0.9637, relative return -14.3203, Sharpe -0.1149, max drawdown -0.9636, IC not significant, capacity-limited trades 2,703, max participation above 1,700%.
- `reversal_20`: rejected for relative return below threshold and drawdown above limit. Total return -0.9760, relative return -14.3326, Sharpe -0.5174, max drawdown -0.9766, significant positive IC, but negative long-short spread and 369 capacity-limited trades.
- `momentum_20`: rejected for relative return below threshold and drawdown above limit. Total return -0.9919, relative return -14.3485, Sharpe -0.6100, max drawdown -0.9947, significant negative IC, and capacity-limited trades 4.

The technical baseline did not produce a rescue candidate. The most actionable conclusion remains architectural rather than parametric: the next factor-mining step should pre-register liquidity-aware or residualized factors instead of searching wider top-N portfolios over existing raw technical or moneyflow scores.

## Holding-Period Sensitivity

The office desktop then tested whether daily turnover was the main failure mode by moving the strongest existing moneyflow-combo candidates to 5-day forward returns and 5-day rebalancing on the combined 2023-2026 store.

`mf_low_minus_volatility_20`, forward5/rebalance5/cost20:

- Top5: rejected for drawdown above limit. Total return 52.8020, relative return 39.4454, Sharpe 0.8870, max drawdown -0.6067, IC p-value 0.0511, capacity-limited trades 54, max participation above 300%, and long-short spread -0.1019.
- Top10: rejected for drawdown above limit. Total return 14.7345, relative return 1.3779, Sharpe 0.7610, max drawdown -0.6159, IC p-value 0.0511, capacity-limited trades 37, max participation above 160%, and long-short spread -0.1019.
- Top20: rejected for relative return below threshold and drawdown above limit. Total return 8.4630, relative return -4.8936, Sharpe 0.6488, max drawdown -0.5490, IC p-value 0.0511, capacity-limited trades 19, max participation above 200%, and long-short spread -0.1019.

`large_minus_liquidity_20`, forward5/rebalance5/cost20:

- Top5: rejected for relative return below threshold and drawdown above limit. Total return 0.1873, relative return -13.1693, Sharpe 0.4440, max drawdown -0.8569, capacity-limited trades 5.
- Top10: rejected for relative return below threshold and drawdown above limit. Total return -0.3379, relative return -13.6945, Sharpe 0.2373, max drawdown -0.8278, capacity-limited trades 7.
- Top20: rejected for relative return below threshold and drawdown above limit. Total return 0.0274, relative return -13.3291, Sharpe 0.3482, max drawdown -0.7626, capacity-limited trades 4.

Longer holding periods do not rescue the current candidates. `mf_low_minus_volatility_20` remains a high-return but non-tradable and non-monotonic shape; `large_minus_liquidity_20` loses most of its edge when moved from 1-day to 5-day holding. This pushes the research direction further toward new liquidity-aware factor construction rather than holding-period parameter sweeps.

## Failure Attribution For Next Factor Design

The office desktop then decomposed the two most informative failed candidates to avoid designing the next batch blindly.

`large_minus_liquidity_20`, combined top5/cost20:

- Worst drawdown ran from 2024-01-02 to 2024-07-09. Strategy return over that span was -60.01% versus -24.54% for the equal-weight benchmark, so the drawdown was not just broad market beta.
- Capacity was not the main cause. Only 2 trades were capacity-limited; median participation was 0.0036%, 99th percentile participation was 0.627%, and max participation was 14.4%.
- The quantile profile was hump-shaped rather than monotonic. Mean forward returns by quantile were 0.53%, 0.68%, 2.33%, 2.41%, and 1.02%, consistent with the negative RankIC warning.
- The 2024Q1 and 2024Q2 trade buckets were the main weak periods, with additive weighted-return sums of -0.2872 and -0.4732. The strategy recovered later, but the interim drawdown is too severe for promotion.

`mf_low_minus_volatility_20`, combined top10/cost20:

- Worst drawdown ran from 2023-08-18 to 2024-07-10. Strategy return over that span was -33.93% versus -23.45% for the equal-weight benchmark.
- Capacity is a real feasibility constraint. The run had 183 capacity-limited trades, 95th percentile participation 2.93%, 99th percentile 9.45%, and max participation 258.6%.
- Low-liquidity names drove both the signal and the implementation problem. The `<=10m` amount bucket had all 183 capacity-limited trades; the `>500m` amount bucket had a negative additive weighted-return sum.
- The quantile profile was non-monotonic: the bottom quantile mean return was 2.86% while the top quantile mean return was only 0.92%, matching the negative long-short spread despite positive IC and RankIC.

Design implication: the next pre-registered factor batch should not simply add a liquidity term to the score. It should either gate out thinly traded names before ranking, residualize moneyflow against liquidity and broad risk, or explicitly target the mid-quantile/tail behavior that current RankIC and quantile diagnostics expose.
