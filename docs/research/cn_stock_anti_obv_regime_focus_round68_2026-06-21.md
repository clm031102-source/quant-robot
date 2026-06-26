# CN Stock Anti-OBV Regime Focus Round 68 - 2026-06-21

## Purpose

Round67 hibernated the daily-basic residual costed bottom-exclusion line because relative improvement did not fix absolute drawdown or Sharpe. Round68 tested whether the public trend-volume inverse signal `anti_obv_breakout_low_tail_20` could work as a simple risk-regime focused standalone factor on the 2015-2025 CN stock authority data.

This was a stop-loss check, not a promotion attempt.

## Experiment

- Config: `configs/experiment_grid_cn_stock_anti_obv_regime_focus_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_anti_obv_regime_focus_round68_20260621`
- Market: CN A-share stocks
- Period: 2015-01-05 through 2025-12-31
- Factor source: `public_trend_volume`
- Factor: `anti_obv_breakout_low_tail_20`
- Horizon: 20
- Execution lag: 1
- Rebalance: 5 and 10
- Top N: 30, 50, 100
- Cost: 10 bps plus 20 bps market impact
- Max participation: 1% ADV
- Regime lookback: 60 and 120

Data manifest was refreshed against `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json` before the formal run. The adjusted-ratio mass-jump warning cleared; the remaining manifest status was `review_required` due to `extreme_return_rows_present`, with no blockers.

## Result

- Cases: 12
- Completed: 12
- Failed: 0
- Accepted/promotable cases: 0
- Best overlap-adjusted Sharpe: 0.0950
- Best total return: 3.43%
- Best relative return: -2370.32%

Best row:

| Case | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Win | Relative | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `CN_anti_obv_breakout_low_tail_20_top50_cost10_reb10_regime120` | 3.43% | 0.29% | 0.0878 | 0.0950 | -33.64% | 50.51% | -2370.32% | rejected |

Other positive-return rows were also economically weak:

- top100, reb10, regime120: total 2.26%, overlap Sharpe 0.0703, relative -2371.49%.
- top30, reb10, regime120: total 0.55%, overlap Sharpe 0.0887, relative -2373.20%.

Regime60 rows were negative and had drawdowns around -62% to -69%.

## Interpretation

`anti_obv_breakout_low_tail_20` keeps some cross-sectional IC, but it does not translate into a usable standalone long-only portfolio. The best case barely earned positive absolute return over the full 2015-2025 sample and was massively behind the benchmark.

This confirms the earlier stop-loss conclusion:

- Do not continue standalone anti-OBV parameter searches.
- Do not treat inverse public trend-volume as a promotion candidate.
- Keep it only as a possible risk-state or exclusion component.

## Direction Change

Round69 should stop single-factor public trend-volume work and test the translation layer directly:

- industry-breadth bridge from stock signals,
- later mapping to liquid ETF/theme representatives only if industry-level evidence exists,
- no new TopN stock sweeps until the bridge gate produces evidence.

Current promotable profitable factors: 0.

Current useful output: a confirmed rejection of standalone anti-OBV regime focus and a forced rotation into stock-to-industry/ETF breadth translation.
