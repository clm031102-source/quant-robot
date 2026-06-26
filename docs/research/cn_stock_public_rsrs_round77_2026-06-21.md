# CN Stock Public RSRS Long-Cycle Audit Round 77 - 2026-06-21

## Scope

Round77 ran the pre-registered public RSRS family on CN stocks using the long-cycle authority bars from 2015-01-05 through 2025-12-31.

This was a public-method rotation after the public risk-filter bridge family was hibernated. The purpose was not to tune windows, but to test whether a known RSRS-style high/low regression signal can translate into a tradable CN stock cross-sectional factor under cost, capacity, drawdown, and overlap-aware return checks.

Source config:

- `configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`

Run output:

- `data/reports/experiment_grid_cn_stock_public_rsrs_round76_20260621/leaderboard.csv`

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Experiment Design

- Market: CN stocks, not ETF rotation.
- Sample: 2015-01-05 to 2025-12-31.
- Factors: `rsrs_slope_18`, `rsrs_zscore_18_60`, `rsrs_right_skew_18_60`, `rsrs_reversal_18_60`.
- Portfolio: top50/top100, rebalance every 10 trading days, 20-day forward horizon, execution lag 1.
- Costs/capacity: 10 bps cost, 20 bps market impact, max participation 1%, portfolio value 1,000,000, target gross exposure 0.6.
- Results: 8 cases completed, 0 failed, 0 no-trade.

## Leaderboard Summary

| Rank | Case | Total return | Annual return | Sharpe | Overlap Sharpe | Win rate | Max DD | RankIC | RankIC t | Decision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `CN_rsrs_reversal_18_60_top50_cost10_reb10` | 67.28% | 2.24% | 0.293 | 0.201 | 48.55% | -44.82% | 0.0214 | 4.77 | rejected |
| 2 | `CN_rsrs_reversal_18_60_top100_cost10_reb10` | 72.07% | 1.79% | 0.272 | 0.191 | 50.19% | -40.92% | 0.0214 | 4.77 | rejected |
| 3 | `CN_rsrs_right_skew_18_60_top100_cost10_reb10` | -29.43% | -1.10% | -0.123 | -0.095 | 48.36% | -62.13% | -0.0214 | -4.77 | rejected |
| 4 | `CN_rsrs_zscore_18_60_top100_cost10_reb10` | -34.50% | -1.29% | -0.157 | -0.117 | 46.41% | -64.61% | -0.0178 | -3.98 | rejected |
| 5 | `CN_rsrs_slope_18_top100_cost10_reb10` | -48.80% | -2.24% | -0.258 | -0.187 | 42.63% | -74.96% | -0.0423 | -8.38 | rejected |
| 6 | `CN_rsrs_right_skew_18_60_top50_cost10_reb10` | -44.12% | -2.47% | -0.260 | -0.206 | 46.42% | -68.25% | -0.0214 | -4.77 | rejected |
| 7 | `CN_rsrs_zscore_18_60_top50_cost10_reb10` | -48.23% | -2.77% | -0.297 | -0.226 | 44.84% | -71.77% | -0.0178 | -3.98 | rejected |
| 8 | `CN_rsrs_slope_18_top50_cost10_reb10` | -59.08% | -3.93% | -0.400 | -0.284 | 40.75% | -79.79% | -0.0423 | -8.38 | rejected |

## Interpretation

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads: 1 factor family direction, `rsrs_reversal_18_60`, with two breadth settings.

The important result is direction, not profitability. The direct RSRS slope/z-score/right-skew variants all had negative RankIC and negative portfolio returns. The reversal version flipped the signal and produced positive total return and significant positive RankIC, but it still failed promotion because it massively underperformed the full-market benchmark and had capacity-limited trades.

This means RSRS is not a ready tradable factor in this project. It is a translation-layer lead: public timing indicators cannot be copied into a cross-sectional stock TopN portfolio without first deciding whether high values mean "buy", "avoid", "exclude bottom", or "neutralize risk exposure".

## Why It Is Still Not Useful Enough

The two best cases are weak:

- Sharpe below 0.30 and overlap-adjusted Sharpe near 0.20.
- Annual return only 1.79%-2.24% despite long-cycle positive total return.
- Relative return around -23x versus the benchmark curve, so the result is not competitive with market exposure.
- Capacity-limited trades remain present under the 1% participation gate.
- Tail IC is not significant for the two reversal cases, so the portfolio edge does not persist cleanly in the selected tail.

The correct classification is therefore: research lead only, no promotion.

## Public-Method Lessons

Public references such as Qlib/Alpha158-style factor sets, Alphalens factor tearsheets, VectorBT portfolio testing, Pyfolio risk attribution, and WorldQuant 101 formulaic alpha collections point to the same workflow improvement:

- first test signal direction, IC/RankIC, quantile monotonicity, turnover, and tail behavior;
- then translate the signal into top selection, bottom exclusion, industry-neutral selection, or risk overlay;
- only then run costed long-cycle portfolio tests.

Round77 confirmed that running every public formula directly as TopN wastes budget when the translation layer is wrong.

Reference URLs:

- Qlib: https://github.com/microsoft/qlib
- Alphalens: https://github.com/quantopian/alphalens
- VectorBT: https://vectorbt.dev/
- Pyfolio: https://github.com/quantopian/pyfolio
- WorldQuant 101 Alphas paper: https://arxiv.org/abs/1601.00991

## Next Direction

Do not expand RSRS windows yet.

Round78 should run a focused RSRS reversal translation audit:

- Alphalens-style quantile shape and turnover review for `rsrs_reversal_18_60`.
- Industry/size-neutral IC audit to check whether the signal is just size, liquidity, or industry exposure.
- Bottom-exclusion audit to test whether RSRS works better as "avoid high RSRS/right-skew names" than as long-only top selection.
- Capacity-safe universe gate check before any wider portfolio rerun.

If these checks do not improve portfolio translation, hibernate RSRS and rotate to another public family rather than tuning RSRS parameters.
