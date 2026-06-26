# CN ETF Public Trend-Volume Round 17

Date: 2026-06-21

## Purpose

Round 17 shifted from CN stock TopN mining back toward the project's practical ETF-rotation objective.

The tested family uses public technical concepts already implemented in the project:

- SuperTrend with volume confirmation,
- smart-money style directional amount pressure,
- OBV breakout,
- anti / contrarian variants.

## Configuration

Config:

- `configs/experiment_grid_cn_etf_public_trend_volume_20260621.json`

Data:

- Source: `data/processed/etf_csv`
- Market: `CN_ETF`
- Assets: 10 liquid ETF symbols
- Date range used by config: 2015-01-05 to 2026-05-22
- Benchmark: `CN_ETF_XSHG_510300`

Grid:

- Factors: 6
- TopN: 1, 2
- Cost: 5 bps, 10 bps
- Rebalance interval: 5, 10
- Regime lookback: 60, 120
- Target gross exposure: 0.8
- Market impact: 2 bps
- Max participation: 10%

## Experiment Evidence

Output:

- `data/reports/experiment_grid_cn_etf_public_trend_volume_20260621`

Result:

- 96 / 96 cases completed.
- 0 failed.
- 0 no-trade.
- 0 capacity-limited cases.
- 0 extreme-trade flags.
- 0 approved cases.

Rejection reasons:

- `relative_return_below_threshold`: 94
- `drawdown_above_limit`: 53

## Best Rows

| Rank | Case | Total return | Relative return | Sharpe | Overlap Sharpe | Max DD | Win rate | RankIC t | Capacity-limited trades |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `smart_money_trend_20_top2_cost5_reb5_regime120` | 0.4705 | 0.1531 | 0.5737 | 0.6431 | -0.2589 | 0.5238 | 1.43 | 0 |
| 2 | `smart_money_trend_20_top1_cost5_reb5_regime120` | 0.3394 | 0.0220 | 0.4398 | 0.5115 | -0.2901 | 0.5143 | 1.43 | 0 |
| 3 | `smart_money_trend_20_top1_cost5_reb10_regime120` | 0.2867 | -0.0307 | 0.4786 | 0.4568 | -0.1686 | 0.5189 | 0.42 | 0 |

## Interpretation

This is a materially better direction than the recent CN stock TopN work.

What improved:

- The best ETF candidate has positive benchmark-relative return.
- Capacity is clean across the grid.
- No data-artifact trades appeared.
- The best candidate is explainable: ETF trend plus directional amount pressure under a 120-day regime filter.

What still fails:

- 0 cases are promotable.
- The best candidate misses the drawdown gate by about 0.9 percentage points.
- RankIC is not statistically significant, likely partly because the ETF universe is small.
- Most variants still fail relative-return gates.
- SuperTrend-only variants are weak; the useful component is the smart-money trend blend, not the SuperTrend family by itself.

## Decision

Research lead:

- `smart_money_trend_20_top2_cost5_reb5_regime120`

Not promotable:

- It fails the drawdown gate.
- It needs stricter out-of-sample / walk-forward validation.
- It needs parameter sensitivity before being trusted.

Rejected as standalone families for now:

- `supertrend_volume_confirmed_10_3_20`
- `anti_supertrend_volume_confirmed_10_3_20`
- most OBV and anti-smart-money variants.

## Next Direction

Round 18 should not invent another raw ETF indicator immediately.

First test whether the one useful ETF lead survives simple risk control:

1. Lower target exposure from 0.8 to 0.6 / 0.5.
2. Keep the same factor and same parameters.
3. Test whether drawdown falls below 25% without destroying positive relative return.
4. Then run walk-forward if the full-sample risk-adjusted row survives.

## Current Conclusion

Round 17 produced 0 new factor names and 0 promotable factors.

It produced the first useful ETF-direction research lead of this cycle:

- `smart_money_trend_20_top2_cost5_reb5_regime120`

This is a better path than continuing CN stock formulas because it is directly aligned with ETF rotation and already has positive benchmark-relative evidence after costs.
