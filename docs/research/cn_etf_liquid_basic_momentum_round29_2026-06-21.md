# CN ETF Liquid Basic Momentum Round 29

Date: 2026-06-21

## Purpose

Round 29 rotated away from the public trend-volume family and tested a basic ETF momentum family.

This followed the Round 28 conclusion: do not keep mutating the same trend-volume family after it fails walk-forward significance.

## Config

Config:

- `configs/walk_forward_cn_etf_liquid_basic_momentum_round29_20260621.json`

Preflight:

- `data/reports/etf_validation_preflight_cn_etf_liquid_basic_momentum_round29_20260621`
- Status: cleared
- Asset count: 264
- Fold count: 4
- Minimum rebalance opportunities: 26
- Median allowed rebalance dates: 26

Walk-forward output:

- `data/reports/walk_forward_cn_etf_liquid_basic_momentum_round29_20260621/walk_forward_leaderboard.csv`

## Tested Family

Factor source:

- `technical`

Factor names:

- `momentum_20`
- `risk_adjusted_momentum_20`
- `momentum_60`
- `risk_adjusted_momentum_60`

Grid:

- TopN: 5
- Cost: 5 bps
- Rebalance: 5 and 10
- Regime filter: false
- Rolling train/test: 756 / 126 trading days
- Folds: 4

## Result

Summary:

- Cases: 8
- Fold rows: 32
- Aggregate accepted: 0
- Aggregate rejected: 8
- Max accepted folds: 3
- Best mean test Sharpe: 0.2013
- Best mean test relative return: 0.0630
- Best mean test annualized return: 0.0213
- Best mean test win rate: 0.5625
- Minimum total test trades per case: 240

## Best Row

Best stability-ranked row:

- Case: `CN_ETF_risk_adjusted_momentum_20_top5_cost5_reb5`
- Accepted folds: 1 / 4
- Mean test Sharpe: 0.2013
- Mean test relative return: 0.0630
- Mean test annualized return: 0.0213
- Mean test win rate: 0.5521
- Worst test drawdown: -0.0728
- Total test trades: 480
- Test mean IC: 0.0327
- Test RankIC t-stat: 0.3470
- Adjusted IC p-value: 1.0
- Validation status: rejected

Rejection reasons:

- `oos_sharpe_below_threshold`
- `relative_return_below_threshold`
- `insufficient_accepted_folds`
- `adjusted_ic_significance_not_passed`

## Interpretation

The basic momentum family did not survive walk-forward.

The evidence is weaker than the best Round 28 trend-volume candidate:

- lower mean OOS Sharpe,
- fewer accepted folds for the top-ranked row,
- no adjusted IC significance,
- weak fourth fold across most candidates.

## Decision

Promotable factors:

- 0

Paper-ready factors:

- 0

Research leads:

- None strong enough to continue within the current basic momentum grid.

## Next Direction

Do not keep mutating basic momentum.

The next factor family should move to a different public ETF idea:

- mean-reversion with liquidity/tail guards,
- drawdown recovery,
- low-volatility defensive rotation,
- breadth/risk-on overlay.

Before any new run:

- keep the Round 25 liquid ETF universe,
- run preflight first,
- use walk-forward before claiming usefulness.
