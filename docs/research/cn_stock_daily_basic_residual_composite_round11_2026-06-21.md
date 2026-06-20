# CN Stock Daily-Basic Residual Composite Round 11

Date: 2026-06-21

## Purpose

Round 11 moved away from single-family moneyflow and standalone public technical factors. The tested thesis was a public-method-inspired residual composite family:

- combine value, low turnover, low tail risk, and short-term reversal components;
- neutralize common size, liquidity, and momentum exposures cross-sectionally;
- evaluate on the full 2015-2025 CN stock authority sample with costs, capacity, regime filtering, overlap-aware statistics, and no parameter tuning after reading the results.

Public references reviewed for workflow direction:

- Microsoft Qlib / RD-Agent style automated factor mining and full research workflow: https://github.com/microsoft/qlib
- Alphalens-style factor evaluation emphasis: IC, quantile spreads, turnover, and return analysis: https://github.com/quantopian/alphalens
- Formulaic price-volume factor templates from 101 Formulaic Alphas: https://arxiv.org/abs/1601.00991

## Added Factors

Factor source: `daily_basic_residual_composite`

- `resid_value_quality_low_vol_20`
- `resid_value_low_turnover_quality_20`
- `resid_value_reversal_low_tail_20`

Reusable implementation:

- `src/quant_robot/factors/daily_basic_residual_composite.py`
- `configs/experiment_grid_cn_stock_daily_basic_residual_composite_fast_20260621.json`

Safety/process improvement:

- Added `exclude_adjusted_ratio_jump_assets` to authority bars config loading.
- Added `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`.
- Clean manifest reduced CN stock bars from 10,759,495 rows / 5,707 assets to 8,416,451 rows / 4,725 assets.
- Clean manifest removed all adjusted-ratio jump rows/assets; remaining warning is `extreme_return_rows_present`.

## Experiment Evidence

Unclean repaired-bars replay:

- 12 / 12 cases completed.
- All cases rejected by `relative_return_below_threshold`.
- `resid_value_low_turnover_quality_20` showed the best IC evidence, but Top100 variants were contaminated by one extreme 600777.SH trade.
- Extreme diagnostic: `CN_XSHG_600777`, signal 2025-04-14, entry 2025-04-15, exit 2025-07-18, gross return 49.93x.

Clean authority-bars replay:

- 12 / 12 cases completed.
- 0 failed, 0 no-trade, 0 capacity-limited trades, 0 extreme-trade flags.
- All cases still rejected by `relative_return_below_threshold`.

Best clean cases:

| Rank | Case | Total return | Sharpe | Overlap Sharpe | Max DD | Win rate | Mean IC | RankIC | RankIC t |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `resid_value_quality_low_vol_20_top50_reb10` | 0.3234 | 0.2839 | 0.2785 | -0.2453 | 0.5246 | 0.0048 | 0.0180 | 1.65 |
| 2 | `resid_value_low_turnover_quality_20_top50_reb10` | 0.2872 | 0.2548 | 0.2761 | -0.2920 | 0.5197 | 0.0188 | 0.0381 | 3.98 |
| 3 | `resid_value_reversal_low_tail_20_top50_reb10` | 0.2497 | 0.2353 | 0.2623 | -0.2582 | 0.5115 | 0.0206 | 0.0371 | 3.82 |
| 5 | `resid_value_low_turnover_quality_20_top50_reb5` | 0.3368 | 0.3683 | 0.2485 | -0.2543 | 0.5125 | 0.0223 | 0.0411 | 6.02 |

## Conclusion

No factor is promotable. Portfolio returns are far below the CN benchmark and all cases fail the relative-return gate.

There is research value, unlike the failed moneyflow-only and direct trend-volume families:

- `resid_value_low_turnover_quality_20` has the strongest clean RankIC evidence: RankIC 0.0411 with t-stat 6.02 on the rebalance-5 sample.
- `resid_value_reversal_low_tail_20` also has persistent clean RankIC and quantile-spread evidence.
- `resid_value_quality_low_vol_20` has the best clean overlap Sharpe in top50/reb10 but weak IC; treat it as a risk-control component, not an alpha lead.

Actionable direction:

- Do not promote any Round 11 standalone portfolio.
- Use the clean authority-bars config for future CN stock factor work.
- Continue with residual composite variants only if they are combined with portfolio construction improvements, sector/industry neutrality, or ETF-breadth aggregation; otherwise the signal is statistically visible but not tradable enough.
- Round 12 should test a different public family or a portfolio-construction layer, not another blind parameter sweep of the same formulas.
