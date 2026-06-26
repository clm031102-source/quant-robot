# CN Stock Public Formula Price-Volume Round 12

Date: 2026-06-21

## Purpose

Round 12 tested a low-complexity public formula family inspired by WorldQuant/Qlib style price-volume expressions. This was intentionally a family rotation away from residual daily-basic composites.

Data policy:

- Authority bars config: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Data manifest: `data/reports/cn_stock_data_manifest_adjusted_ratio_clean`
- Clean bars: 8,416,451 rows, 4,725 CN stock assets, adjusted-ratio jump rows/assets = 0.

## Added Factors

Factor source: `public_formula_price_volume`

- `formula_pv_corr_reversal_20`
- `formula_volume_contraction_reversal_20`
- `formula_range_contraction_breakout_20`

Implementation:

- `src/quant_robot/factors/public_formula_price_volume.py`
- `configs/experiment_grid_cn_stock_public_formula_price_volume_fast_20260621.json`

## Experiment Evidence

Grid:

- 3 factors
- TopN: 50, 100
- Rebalance interval: 5, 10
- Cost: 10 bps
- Forward horizon: 20
- Regime filter: enabled, lookback 120
- Market impact/capacity: enabled

Result:

- 12 / 12 cases completed.
- 0 failed, 0 no-trade, 0 extreme-trade flags.
- All cases rejected by `relative_return_below_threshold`.
- Several cases also triggered `capacity_limited_trades_present`; the family is not capacity-clean in broader TopN variants.

Best cases by overlap-adjusted Sharpe:

| Rank | Case | Total return | Sharpe | Overlap Sharpe | Max DD | Win rate | Mean IC | RankIC | RankIC t | Long-short mean |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `formula_pv_corr_reversal_20_top50_reb5` | 0.1389 | 0.1803 | 0.1056 | -0.2455 | 0.4410 | 0.0420 | 0.0757 | 10.88 | 0.0082 |
| 2 | `formula_pv_corr_reversal_20_top100_reb5` | 0.1540 | 0.1723 | 0.0967 | -0.2623 | 0.4337 | 0.0420 | 0.0757 | 10.88 | 0.0082 |
| 5 | `formula_volume_contraction_reversal_20_top100_reb5` | -0.0289 | 0.0166 | 0.0103 | -0.4210 | 0.4342 | 0.0505 | 0.0793 | 10.25 | 0.0103 |

## Interpretation

This family has the strongest statistical cross-sectional signal found in this round sequence:

- `formula_pv_corr_reversal_20`: RankIC around 0.076, t-stat 10.88.
- `formula_volume_contraction_reversal_20`: RankIC around 0.080, t-stat 10.25.
- Quantile spreads and long-short means are positive.

But it is not a promotable long-only strategy:

- TopN long-only portfolios badly underperform the CN benchmark.
- Some Top100 variants hit capacity limits.
- The top quantile is only mildly positive while the bottom quantile is strongly negative; much of the edge is in avoiding/shorting bad names, not in buying winners.
- Tail IC is weak or negative for the best IC case, so realized portfolio holdings do not preserve the raw factor edge.

## Conclusion

No Round 12 factor is promotable as a standalone long-only stock portfolio signal.

Research value:

- `formula_pv_corr_reversal_20` is a strong ranking / exclusion signal.
- `formula_volume_contraction_reversal_20` is a strong long-short spread signal but not capacity-clean enough and not long-only profitable.

Next action:

- Stop testing more standalone public formula TopN grids for now.
- The next useful work is a bridge layer: turn high-IC stock factors into sector/theme/ETF breadth, exclusion overlays, or market-timing/risk controls.
- If staying in CN stock, test long-only portfolios with explicit bottom-quantile exclusion and benchmark-beta awareness instead of naive TopN ranking.
