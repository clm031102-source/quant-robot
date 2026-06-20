# CN Stock Public Formula Momentum Confirmation Round 14

Date: 2026-06-21

## Purpose

Round 14 tested whether the strongest Round 12 public price-volume ranking signals could be converted into buyable long-only portfolios by adding a simple 60-day momentum confirmation layer.

This was not a new blind family search. It was a targeted check of the Round 13 audit hypothesis: the raw formula signals have IC, but their edge may not survive naive TopN long-only construction.

Data policy:

- Authority bars config: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Data manifest: `data/reports/cn_stock_data_manifest_adjusted_ratio_clean`
- Clean bars: 8,416,451 rows, 4,725 CN stock assets, adjusted-ratio jump rows/assets = 0.

## Added Factors

Factor source: `public_formula_price_volume`

- `formula_pv_corr_momentum_confirmed_20_60`
- `formula_volume_contraction_momentum_confirmed_20_60`

Implementation:

- `src/quant_robot/factors/public_formula_price_volume.py`
- `configs/experiment_grid_cn_stock_public_formula_price_volume_momentum_confirmed_fast_20260621.json`

The variants keep the public formula family explainable, but require non-negative 60-day momentum and avoid high downside-volatility tails.

## Experiment Evidence

Grid:

- 2 factors
- TopN: 50, 100
- Rebalance interval: 5, 10
- Cost: 10 bps
- Forward horizon: 20
- Regime filter: enabled, lookback 120
- Market impact/capacity: enabled

Result:

- 8 / 8 cases completed.
- 0 failed, 0 no-trade, 0 extreme-trade flags.
- 8 / 8 cases rejected.
- Every case failed `relative_return_below_threshold`.
- Every case also triggered `capacity_limited_trades_present`.

Best cases by overlap-adjusted Sharpe:

| Rank | Case | Total return | Sharpe | Overlap Sharpe | Max DD | Win rate | Mean IC | RankIC | RankIC t | Long-short mean | Capacity-limited trades |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `formula_pv_corr_momentum_confirmed_20_60_top100_reb10` | 0.1601 | 0.1253 | 0.0972 | -0.3866 | 0.4990 | 0.0262 | 0.0276 | 3.14 | 0.0035 | 7 |
| 2 | `formula_pv_corr_momentum_confirmed_20_60_top50_reb10` | -0.0071 | 0.0596 | 0.0462 | -0.4645 | 0.4835 | 0.0262 | 0.0276 | 3.14 | 0.0035 | 9 |
| 4 | `formula_volume_contraction_momentum_confirmed_20_60_top100_reb10` | -0.0864 | 0.0104 | 0.0096 | -0.3930 | 0.4968 | 0.0200 | 0.0436 | 4.96 | 0.0073 | 7 |

## Interpretation

Momentum confirmation did not solve the real problem.

What improved:

- Extreme adjusted-price artifacts stayed removed on the clean authority dataset.
- The confirmed factors still show statistically positive RankIC, especially the volume-contraction variant.

What failed:

- Long-only returns remain poor after costs.
- Drawdowns are still too large.
- Capacity limits are worse than Round 12 because the confirmation layer concentrates the portfolio into less tradable names.
- The best signal remains a relative ranking / exclusion signal, not a standalone long-only buy signal.

## Stop-Loss Decision

Stop adding more confirmation filters to the same public formula factors until the project has a portfolio translation layer.

Do not spend the next rounds on:

- extra momentum windows,
- extra downside-volatility gates,
- extra TopN/rebalance sweeps,
- more formula variants tested only as naive long-only TopN baskets.

## Next Direction

Round 15 should diagnose and then build around the IC-to-portfolio gap:

1. Measure top-vs-bottom quantile contribution and whether the edge is mostly an exclusion/short signal.
2. Add factor-to-portfolio diagnostics for capacity, beta, drawdown, and regime dependence.
3. Prefer bottom-quantile exclusion, ETF/theme breadth translation, or market-risk overlays over more raw factor invention.

## Current Conclusion

Round 14 produced 2 new registered factors and 0 promotable factors.

Both factors are useful negative evidence. They confirm that the current bottleneck is not a lack of public formula ideas; it is converting statistically significant stock rankings into deployable, capacity-clean, long-only portfolio returns.
