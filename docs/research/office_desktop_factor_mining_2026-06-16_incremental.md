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

## Directional And Liquidity-Gate Probes

Before adding production factor code, the office desktop ran temporary research-only probes in `data/reports` to test whether simple transformations were worth pre-registering.

Directional and nonlinear probes:

- `inverse_mf_low_minus_volatility_20` failed across top5/top10/top20. The inverse had significant negative IC, drawdowns near -100%, and hundreds of capacity-limited trades.
- `inverse_large_minus_liquidity_20` also failed across top5/top10/top20, with drawdowns near -100% and severe participation pressure.
- Rank-target transforms of `large_minus_liquidity_20` that selected names closest to the 65th or 75th percentile removed most capacity pressure but still had insignificant IC, negative relative return, and drawdowns around -85% to -88%.

Signal-date amount gates:

- Applying `>=10m`, `>=50m`, `>=100m`, `10m-500m`, and `50m-500m` amount filters before ranking removed or nearly removed capacity-limited trades, but did not produce an approved candidate.
- For `mf_low_minus_volatility_20`, the best-looking gated row was `10m-500m/top20`: capacity-limited trades 0, total return 7.1248, but relative return -6.2318, max drawdown -0.6803, and IC no longer significant.
- For `large_minus_liquidity_20`, the best-looking gated row was `>=100m/top5`: capacity-limited trades 0, total return 9.6189, but relative return -3.7377, max drawdown -0.8051, and IC no longer significant.

These probes reject three easy next steps: simple inversion, percentile targeting, and standalone amount gating. The useful next design should combine gates with a new score, not apply gates after a score whose edge depends on the excluded names.

## Residualized Liquidity-Aware Probe

The office desktop then tested temporary residualized scores without adding production factor code. The most useful construction was:

`resid_large_liq_vol_amt_20`: cross-sectional residual of large-order net flow after removing same-day 20-day Amihud liquidity, 20-day volatility, and log amount. The probe then required signal-day amount `>=100m`, applied a positive equal-weight market regime filter, and selected top5.

Key combined-sample results:

- No-regime top5 with amount `>=100m`: significant positive IC, capacity-limited trades 0, total return 17.8722, relative return 4.5156, but max drawdown -0.7551.
- Regime120 top5: significant positive IC, capacity-limited trades 0, total return 41.0642, relative return 27.7076, Sharpe 1.0749, max drawdown -0.3191.
- Regime150 top5: significant positive IC, capacity-limited trades 0, total return 67.6590, relative return 54.3024, Sharpe 1.1412, max drawdown -0.2859.
- Regime180 top5: significant positive IC, capacity-limited trades 0, total return 38.1081, relative return 24.7515, Sharpe 1.0788, max drawdown -0.2859.
- Regime252 top5: significant positive IC, capacity-limited trades 0, total return 41.3360, relative return 27.9794, Sharpe 1.1013, max drawdown -0.2859.

Split-window check for the best temporary row, regime150/top5:

- 2023H2 and 2024H1 had no trades because the regime filter blocked those weak market windows.
- 2024H2: approved by simple return/drawdown/capacity gates. Total return 1.7672, relative return 1.4761, Sharpe 6.7184, max drawdown -0.2077, capacity-limited trades 0. IC was not significant.
- 2025H1: approved by simple gates. Total return 0.8500, relative return 0.6730, Sharpe 2.7597, max drawdown -0.2859, capacity-limited trades 0. IC was not significant.
- 2025H2: approved by simple gates. Total return 0.6849, relative return 0.5118, Sharpe 2.3735, max drawdown -0.1750, capacity-limited trades 0. IC was significant positive.
- 2026H1: approved by simple gates. Total return 0.2543, relative return 0.2511, Sharpe 1.4231, max drawdown -0.2021, capacity-limited trades 0. IC was not significant.

Audit judgment: this is the first temporary probe to clear the basic combined-sample return, drawdown, and capacity gates. It is still only a strict-validation candidate, not a promotion. Risks remain: the regime filter excludes the hardest early windows, half-year IC is often not significant, RankIC remains negative, and the factor exists only as a temporary research script. The next productive code task is to pre-register this residualized liquidity-aware factor family and run formal rolling walk-forward.

## Production Residual Matrix Recheck

After the laptop integrated the residualized moneyflow method into production factor code, the office desktop rebased the mining work onto that method update and reran the combined 2023-2026 sample using the formal factor builder. The full rolling walk-forward grid was too slow on the office desktop because the current validation path recomputes residual factors per case and per fold. The useful office workflow was therefore to compute the production factor matrix once, cache it locally under `data/reports`, and audit regimes from that matrix.

The production matrix covered `large_minus_liquidity_20`, `large_resid_liq_vol_amt_20`, `large_resid_liq_vol_amt_gate_20`, and `large_resid_liquidity_20` with 14,283,928 factor rows. Local artifact path: `data/reports/desktop_factor_mining_20260616_continue/20260616_office_production_residual_factor_matrix_probe/`.

Best combined-sample rows, top5/cost20/1,000,000 portfolio value/10 bps market impact:

- `large_resid_liq_vol_amt_gate_20`, regime150: approved by simple return/drawdown/capacity/IC gates. Total return 67.6590, relative return 54.3024, Sharpe 1.1412, max drawdown -0.2859, capacity-limited trades 0, max participation 1.75%, mean IC 0.00796, IC p-value 0.00228.
- `large_resid_liq_vol_amt_gate_20`, regime252: approved by simple gates. Total return 41.3360, relative return 27.9794, Sharpe 1.1013, max drawdown -0.2859, capacity-limited trades 0, mean IC 0.00810, IC p-value 0.00208.
- `large_resid_liq_vol_amt_gate_20`, regime180: approved by simple gates. Total return 38.1081, relative return 24.7515, Sharpe 1.0788, max drawdown -0.2859, capacity-limited trades 0, mean IC 0.00760, IC p-value 0.00334.

The ungated production residual score had much larger raw returns but failed capacity review: `large_resid_liq_vol_amt_20` top5/no-regime had 160 capacity-limited trades and max participation above 500%; regime150 still had 58 capacity-limited trades. This confirms that the amount gate is not cosmetic. It is the difference between a high-return but non-tradable residual score and a capacity-clean strict-validation candidate.

Split-window check on the three approved gated rows:

- 2023H2 and 2024H1 had no trades because the positive market-regime filter blocked those windows.
- Regime150/top5 passed simple gates in 2024H2, 2025H1, 2025H2, and 2026H1, with capacity-limited trades 0 in every traded split. Returns were strongest in 2024H2 and weakest but still positive in 2026H1.
- Regime180/top5 and regime252/top5 also passed simple gates in every traded split. Regime252 gave the best 2025H1 and 2026H1 split returns, while regime150 gave the best full-sample relative return.
- Half-year IC remains unstable: only 2025H2 was significant positive across these split checks. RankIC remains negative in the combined sample, so the factor is still tail-driven rather than smoothly monotonic.

Audit judgment: the laptop-integrated production factor reproduces the temporary probe. `large_resid_liq_vol_amt_gate_20` top5 with regime150/180/252 should stay in the strict-validation queue. It is not promotion-ready because the regime filter avoids the hardest early windows and split IC is not consistently significant. The laptop framework now addresses the office runtime bottleneck with `precompute_factor_matrix`; the desktop still needs a formal rolling walk-forward run before any promotion discussion.

## Signal Amount And Rank-Window Probe

The office desktop then reused the cached production factor matrix to test signal-day amount bands and rank-window offsets for `large_resid_liq_vol_amt_gate_20`. This was a no-lookahead probe: filters used same-day signal amount and same-day factor ranks before selection. The local run evaluated 120 combinations across regime150/180/252, amount bands, and rank windows.

No combination passed the stricter tail-selection gate. The main reason was not capacity; capacity-limited trades stayed at 0 for the leading rows. The failure was that IC measured only on the preselected tradable tail was not significant, and several higher-return variants increased drawdown.

Key observations:

- The highest-return row, `gte100m/r1_3/top3/regime150`, had total return 84.6445 and relative return 71.2879, but max drawdown worsened to -0.3643 and selected-tail IC was not significant.
- The original `gte100m/r1_5/top5/regime150` shape retained total return 67.6590, relative return 54.3024, and max drawdown -0.2859, but selected-tail IC was not significant in this stricter tail-only view.
- Excluding the 500m-1b signal-amount band improved drawdown for `r1_5/regime150` to -0.2579, but relative return fell to 38.4864 and selected-tail IC remained not significant.
- Raising the signal-day amount floor to 200m, 500m, or 1b generally reduced the edge. The best `gte200m` row had relative return 32.1945 but max drawdown -0.4983; the best `gte500m` row had relative return only 6.0874 and max drawdown -0.5276.

Audit judgment: amount-band tweaks and rank-window offsets do not produce a better candidate than the existing `large_resid_liq_vol_amt_gate_20` top5 regime family. The useful method improvement is to add a formal tail-selection IC diagnostic to validation, because full-universe IC can look significant while the actually traded tail is not significant.

## Precompute Desktop Validation Slice

After pulling the laptop method update, the office desktop tested the new `precompute_factor_matrix` validation path against the local combined store. The temporary office config reused the official residual-regime validation grid but pointed `moneyflow_input_root` at `data/processed/office_desktop_20260616_combined_research/processed` and narrowed the factor set to `large_resid_liquidity_20` plus `large_resid_liq_vol_amt_gate_20`.

The run was stopped by a 30-minute local timeout before it produced a complete rolling-validation summary. It still produced useful partial evidence:

- Fold 01 test rows were all `no_trades`; the strategy stayed in cash while the benchmark returned 0.3529, so all rows were rejected for relative return.
- Fold 02 train produced completed rows. The strongest capacity-clean gated row was `large_resid_liq_vol_amt_gate_20/top5/cost20/regime150`: trades 95, total return 0.8707, relative return 0.8188, Sharpe 13.4491, max drawdown -0.0726, capacity-limited trades 0, but IC was not significant over only 19 observations.
- Fold 02 test rows were again all `no_trades`, with relative return -0.0006 and insufficient IC data.
- Fold 03 train had started but the run did not finish, so it is not usable as validation evidence.

Audit judgment: the laptop precompute work is the right direction and avoids repeated residual-factor recomputation, but full rolling validation is still heavy for the office desktop on this grid. The partial results also reinforce the main risk in the candidate: the positive-regime filter avoids early weak windows, which can create no-trade test folds. For promotion work, the next framework task should be checkpoint/resume or thinner fold scheduling; for office mining, cached matrix audits remain the efficient path.

## Large Residual Liquidity Matrix Audit

The office desktop then used the cached production factor matrix to audit `large_resid_liquidity_20` directly, without recomputing residual factors. The run covered 16 combinations across top5/top10, cost20/cost30, and none/regime150/regime180/regime252. No row passed the simple promotion gate.

Key combined-sample rows:

- Top5/cost20/no-regime had very large raw performance and significant IC: total return 1187.6564, relative return 1174.2998, Sharpe 1.1249, mean IC 0.0106, IC p-value 3.35e-09. It was rejected for max drawdown -0.5238 and severe capacity pressure: 171 capacity-limited trades and max participation above 500%.
- Top5/cost20/regime150 improved drawdown to -0.1773 and kept significant IC, with total return 835.9761 and relative return 822.6195. It still failed the simple gate because it had 61 capacity-limited trades and max participation around 75.9%.
- Top5/cost20/regime252 and regime180 showed the same shape: strong returns, significant positive IC, acceptable drawdown, but 55-57 capacity-limited trades.
- Cost30 variants reduced returns and did not solve the capacity issue.

Split-window review shows why this should not be promoted:

- The no-regime version traded through 2023H2 and 2024H1, but 2024H1 was deeply negative despite positive full-sample IC.
- Regime150 blocked 2023H2 and 2024H1, then produced positive traded splits from 2024H2 through 2026H1. However, every traded split still had capacity-limited trades.
- RankIC remained negative in the combined sample, so the signal is still a tail-selection effect rather than a smooth cross-sectional ordering.

Audit judgment: `large_resid_liquidity_20` is rejected as a tradable candidate. It is useful research evidence because liquidity residualization alone creates a strong but capacity-unsafe tail. The amount gate in `large_resid_liq_vol_amt_gate_20` is necessary, not optional, and the strict-validation queue should continue to focus on the gated residual factor family rather than promoting the ungated liquidity residual.
