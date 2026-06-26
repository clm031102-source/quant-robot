# CN ETF Liquid Public Trend-Volume No-Regime Round 28

Date: 2026-06-21

## Purpose

Round 28 fixed the validation path after Round 27 showed that the regime-filtered walk-forward setup had too few tradable test dates.

This round did not add new factor parameters. It reran the same frozen public trend-volume candidates without the restrictive regime filter.

## Process Fix

ETF validation preflight was updated and tested so it respects `asset_universe_path`.

Relevant files:

- `src/quant_robot/ops/etf_validation_preflight.py`
- `tests/unit/test_etf_validation_preflight.py`
- `src/quant_robot/validation/walk_forward.py`
- `tests/unit/test_walk_forward.py`

The no-regime walk-forward config passed preflight:

- Asset count: 264
- Fold count: 4
- Minimum rebalance opportunities: 26
- Median allowed rebalance dates: 26
- Blockers: none

## Config

Config:

- `configs/walk_forward_cn_etf_liquid_public_trend_volume_no_regime_round28_20260621.json`

Output:

- `data/reports/walk_forward_cn_etf_liquid_public_trend_volume_no_regime_round28_20260621/walk_forward_leaderboard.csv`

Frozen cases:

- `supertrend_volume_confirmed_10_3_20`, Top5, rebalance 5 and 10
- `smart_money_trend_20`, Top5, rebalance 5 and 10
- `obv_breakout_low_tail_20`, Top5, rebalance 5 and 10
- Cost: 5 bps
- Regime filter: false

## Result

Summary:

- Cases: 6
- Folds: 4
- Aggregate accepted: 0
- Aggregate rejected: 6
- Fold rows: 24
- Minimum total test trades per case: 240
- Maximum accepted folds for a single candidate: 3
- Best mean test Sharpe: 0.6701
- Best mean test relative return: 0.0800
- Best mean test annualized return: 0.0605
- Best mean test win rate: 0.5208

## Best Candidate

Best row:

- Case: `CN_ETF_smart_money_trend_20_top5_cost5_reb5`
- Accepted folds: 3 / 4
- Mean test Sharpe: 0.6701
- Mean test relative return: 0.0800
- Mean test annualized return: 0.0605
- Mean test win rate: 0.5208
- Worst test drawdown: -0.0776
- Total test trades: 480
- Test mean IC: 0.0224
- Test RankIC t-stat: -0.0002
- Adjusted IC p-value: 1.0
- Validation status: rejected

Rejection reasons:

- `oos_sharpe_below_threshold`
- `adjusted_ic_significance_not_passed`

## Interpretation

Removing the regime filter fixed the sample-size problem, but it did not produce a promotable factor.

The best candidate is now a real research lead rather than a broken-validation artifact:

- enough trades,
- moderate OOS Sharpe,
- 3 accepted folds out of 4,
- tolerable drawdown.

But it still fails the key evidence standard:

- IC evidence is not significant after multiple-testing adjustment.
- One fold still fails OOS Sharpe.
- Mean test annualized return is modest.

## Decision

Promotable factors:

- 0

Paper-ready factors:

- 0

Research leads:

- `CN_ETF_smart_money_trend_20_top5_cost5_reb5`

Do not keep mutating the same trend-volume family now. It has been tested full-sample, regime-filtered WF, and no-regime WF. The best lead is worth tracking, but not worth more blind parameter search.

## Next Direction

Round 29 should rotate to a different public ETF factor family, using the same Round 25 filtered universe and no-regime preflight discipline.

Preferred next family:

- relative strength / dual momentum,
- volatility-adjusted momentum,
- low-volatility trend,
- drawdown recovery.

The same rules remain:

- preflight before walk-forward,
- no promotion from full-sample alone,
- transaction costs and market impact enabled,
- count all rejected cases.
