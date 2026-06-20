# CN Stock Anti Trend-Volume Round 8

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional alpha
- Data: repaired authority CN bars, 2015-01-05 to 2025-12-31
- Config: `configs/experiment_grid_cn_stock_public_trend_volume_anti_fast_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_public_trend_volume_anti_fast_20260621_repaired`

## Why This Round Exists

Round 7 showed statistically significant negative IC for public trend-volume continuation. Round 8 pre-registered the inverse hypothesis: in this CN stock universe, high trend plus volume confirmation may be overextension/crowding risk, so the opposite side may carry the usable signal.

## Long-Cycle Fast Grid

- Cases: 3
- Completed: 3
- Failed/no-trade: 0
- Factor matrix rows: 32,278,485
- IC observations: 526
- TopN/cost/rebalance: top100, 10 bps, rebalance every 5 bars
- Holding/execution: forward horizon 20, execution lag 1

| factor | decision | total return | relative return | Sharpe | overlap-adj Sharpe | max DD | win rate | mean IC | mean RankIC | cap-limited trades | extreme flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `anti_obv_breakout_low_tail_20` | rejected | 0.50 | -37.27 | 0.238 | 0.135 | -57.34% | 47.25% | 0.0341 | 0.0541 | 1 | false |
| `anti_smart_money_trend_20` | rejected | -0.17 | -37.94 | -0.040 | -0.021 | -75.12% | 45.84% | 0.0491 | 0.0584 | 5 | false |
| `anti_supertrend_volume_confirmed_10_3_20` | rejected | -0.29 | -38.06 | -0.109 | -0.056 | -81.63% | 43.63% | 0.0450 | 0.0568 | 1 | false |

## Audit Read

The inversion improved the statistical direction but did not produce a deployable factor.

Positive:

- All three inverse candidates have positive IC and positive RankIC.
- Extreme trade flags cleared.
- `anti_obv_breakout_low_tail_20` produced positive total return.

Blocking:

- All candidates still underperform the CN benchmark by a very large margin.
- `anti_obv_breakout_low_tail_20` still has max drawdown worse than -50%.
- Overlap-adjusted Sharpe remains far below the 0.5 walk-forward budget threshold.
- Capacity-limited trades remain present.
- IC strength again does not translate into strong top-N portfolio performance.

## Decision

No Round 8 factor is promotable.

`anti_obv_breakout_low_tail_20` is the only Round 8 research lead. Round 9 should test whether tighter portfolio construction helps:

- smaller topN;
- slower rebalance interval;
- market regime filter;
- same repaired data and same long-cycle full-sample gate.
