# CN ETF Smart-Money Walk-Forward Round 19

Date: 2026-06-21

## Purpose

Round 19 tested whether the Round 18 full-sample ETF candidate survives out-of-sample walk-forward validation.

Frozen candidate:

- Factor: `smart_money_trend_20`
- Market: `CN_ETF`
- TopN: 2
- Cost: 5 bps
- Rebalance interval: 5
- Regime lookback: 120
- Target gross exposure: 0.6

This round deliberately did not search new parameters. The goal was to test whether the full-sample approval was robust or just a regime / sample artifact.

## Configuration

Config:

- `configs/walk_forward_cn_etf_smart_money_exposure06_20260621.json`

Output:

- `data/reports/walk_forward_cn_etf_smart_money_exposure06_20260621`

Walk-forward setup:

- Rolling train window: 756 trading days
- Rolling test window: 126 trading days
- Step: 63 trading days
- Minimum accepted folds: 3
- Minimum OOS trades per fold: 20
- Strict split check: pass
- Hypothesis count: 1

## Result

| Metric | Value |
|---|---:|
| Cases | 1 |
| Folds | 42 |
| Accepted folds | 0 |
| Rejected folds | 42 |
| Mean test Sharpe | -0.0727 |
| Mean test relative return | -0.0086 |
| Mean test win rate | 0.2560 |
| Mean stability score | -2.8565 |
| Total test trades | 114 |
| Capacity-limited trades | 0 |
| Adjusted IC significance passed | false |

Fold rejection reasons:

- `test_not_completed`: 42 / 42
- `insufficient_oos_trades`: 42 / 42
- `relative_return_below_threshold`: 22 / 42
- `oos_sharpe_below_threshold`: 11 / 42
- `train_not_completed`: 2 / 42

## Interpretation

The Round 18 candidate does not survive walk-forward validation.

The strongest failure is not capacity or cost. The strongest failure is sample stability:

- Every test fold failed the minimum validation gate.
- Every fold had insufficient out-of-sample trades under the current 20-trade requirement.
- Average OOS relative return was negative.
- OOS RankIC was not stable or significant.
- The high and low fold Sharpes are not trustworthy because many folds only had a handful of trades.

The full-sample approval in Round 18 was therefore a false positive under the stricter validation protocol.

## Decision

Do not promote:

- `CN_ETF_smart_money_trend_20_top2_cost5_reb5_regime120`
- target gross exposure: 0.6

Mark it as:

- full-sample validation candidate,
- walk-forward rejected,
- useful as a lesson about ETF regime dependence and low fold-level trade counts.

Do not spend more time tuning exposure on this same candidate unless a separate portfolio-construction change first fixes the low trade-count problem.

## Next Direction

Round 20 should not mutate this exact smart-money candidate again.

The next useful direction is to improve the ETF validation design before mining more ETF signals:

1. Use a larger ETF universe if local data supports it.
2. Prefer strategy families with more fold-level trade opportunities.
3. Test public, economically interpretable families: trend strength, relative momentum, low volatility, drawdown recovery, breadth / risk-on filters, and volatility-adjusted rotation.
4. Require walk-forward evidence before treating any full-sample approval as useful.

## Current Conclusion

Round 19 produced 0 new factor names and 0 promotable factors.

It invalidated the only current-cycle full-sample approved ETF candidate. This is a negative result, but it is useful because it prevents further overfitting around a weak signal.
