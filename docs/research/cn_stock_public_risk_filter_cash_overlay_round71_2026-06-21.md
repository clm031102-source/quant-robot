# CN Stock Public Risk-Filter Cash Overlay Round 71 - 2026-06-21

## Purpose

Round67-69 showed the same pattern repeatedly:

- stock factors and risk filters can identify weak tails;
- direct top-stock or top-industry buying remains low Sharpe;
- max drawdown is the main blocker.

Round71 tested the cheapest possible cash overlay before writing new dynamic regime code: lower static gross exposure for the existing public risk-filter bridge bottom-exclusion portfolio.

This checks whether the previous -60% drawdown problem is just too much gross exposure, or whether the return stream itself is low quality.

## Setup

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Factor source: `daily_basic_public_risk_filter_bridge`
- Factors:
  - `risk_filter_bridge_equal_20`
  - `risk_filter_bridge_agreement_20`
  - `risk_filter_bridge_anti_obv_weighted_20`
- Portfolio construction: exclude bottom 20%, hold the kept basket
- Rebalance: 10
- Holding period: 20
- Cost: 10 bps plus 20 bps market impact
- Liquidity floor: entry amount >= 10,000,000
- Portfolio value: 1,000,000
- Max participation: 1% ADV

## Static Exposure Results

Best factor in all three exposure runs:

`risk_filter_bridge_anti_obv_weighted_20`

| Target Gross Exposure | Total Return | Relative Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Positive Relative Folds | Capacity Limited |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.4 | 13.98% | 12.86% | 0.0920 | 0.0687 | -30.59% | 46.83% | 10/11 | 0 |
| 0.5 | 16.64% | 16.24% | 0.0920 | 0.0686 | -36.91% | 46.83% | 10/11 | 0 |
| 0.6 | 18.89% | 19.62% | 0.0920 | 0.0686 | -42.77% | 46.83% | 10/11 | 0 |

Outputs:

- `data/reports/bottom_exclusion_portfolio_public_risk_filter_round71_20260621_reb10_exposure04`
- `data/reports/bottom_exclusion_portfolio_public_risk_filter_round71_20260621_reb10_exposure05`
- `data/reports/bottom_exclusion_portfolio_public_risk_filter_round71_20260621_reb10_exposure06`

## Interpretation

Static cash allocation helps drawdown mechanically, but it does not fix the strategy.

Evidence:

- Lower exposure reduced max drawdown from the earlier ~-62% area to -30.6% at 0.4 exposure.
- Relative return stayed positive across 10/11 yearly folds for the best factor.
- Capacity was not a blocker.

Blocking evidence:

- Sharpe stayed around 0.09 across all exposure levels.
- Overlap-adjusted Sharpe stayed around 0.069.
- Win rate stayed below 47%.
- Exposure scaling did not change the return quality; it only scaled the same weak stream.
- No case met the costed risk-filter candidate gate.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research lead:

- `risk_filter_bridge_anti_obv_weighted_20` remains useful only as a risk-filter component.

Retire as alpha-improvement path:

- static low-exposure scaling by itself.

## Next Direction

Round72 should test a dynamic market-state/cash overlay instead of more static exposure values.

Pre-registered thesis:

The signal may be useful only when broad market conditions are not hostile. A dynamic overlay must improve drawdown and overlap-adjusted Sharpe without deleting most signal dates. If it only removes evidence or keeps Sharpe near 0.07, this whole public risk-filter bridge line should be hibernated.
