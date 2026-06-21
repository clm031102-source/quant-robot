# CN ETF Liquid Public Trend-Volume Walk-Forward Round 27

Date: 2026-06-21

## Purpose

Round 27 froze the best Round 26 filtered ETF public trend-volume candidates and ran rolling walk-forward validation.

This was required because Round 26 was full-sample discovery only.

## Config

Config:

- `configs/walk_forward_cn_etf_liquid_public_trend_volume_round27_20260621.json`

Universe:

- Round 25 liquid-continuous ETF universe
- 264 selected ETFs

Walk-forward:

- Rolling train days: 756
- Rolling test days: 126
- Rolling step days: 63
- Folds: 4
- Min accepted folds: 2
- Min test trades: 20
- Min test Sharpe: 0
- Min test relative return: 0
- Max test drawdown: 25%
- Multiple-testing alpha: 0.05

Frozen cases:

- `supertrend_volume_confirmed_10_3_20`, Top5, rebalance 5 and 10
- `smart_money_trend_20`, Top5, rebalance 5 and 10
- `obv_breakout_low_tail_20`, Top5, rebalance 5 and 10
- Cost: 5 bps
- Regime lookback: 60

## Result

Output:

- `data/reports/walk_forward_cn_etf_liquid_public_trend_volume_round27_20260621/walk_forward_leaderboard.csv`

Summary:

- Cases: 6
- Folds: 4
- Accepted aggregate candidates: 0
- Rejected aggregate candidates: 6
- Max accepted folds for a single candidate: 2
- Best mean test Sharpe: 0.0903
- Best mean test relative return: 0.0568
- Best mean test annualized return: 0.0008
- Best mean test win rate: 0.3466

## Best Aggregate Row

Best stability-ranked row:

- Case: `CN_ETF_smart_money_trend_20_top5_cost5_reb5_regime60`
- Accepted folds: 2 / 4
- Mean test Sharpe: 0.0903
- Mean test relative return: 0.0568
- Mean test annualized return: 0.0008
- Mean test win rate: 0.3466
- Worst test drawdown: -0.0424
- Total test trades: 85
- Adjusted IC p-value: 1.0
- Validation status: rejected

Rejection reasons:

- `test_not_completed`
- `insufficient_oos_trades`
- `oos_sharpe_below_threshold`
- `adjusted_ic_significance_not_passed`

## Preflight Postmortem

After the run, the ETF validation preflight was executed against the same config:

```powershell
python scripts\run_etf_validation_preflight.py --config configs\walk_forward_cn_etf_liquid_public_trend_volume_round27_20260621.json --source processed-bars --data-root data\processed\tushare_etf_wide_history_2023_2026 --output-dir data\reports\etf_validation_preflight_cn_etf_liquid_public_trend_volume_round27_20260621 --allow-blocked
```

Preflight result:

- Status: blocked
- Median regime-allowed rebalance dates: 6.5
- Minimum allowed rebalance dates: 2
- Minimum rebalance opportunities: 26
- Blocker: `median_regime_allowed_rebalance_dates_below_minimum`

This means the Round 27 walk-forward should have been blocked before running.

The regime filter left too few valid rebalance dates in the test folds, causing many fold-level cases to have 0 or 10 trades.

## Interpretation

No candidate survived walk-forward.

This is not a clean rejection of the factor family alone. It is also a rejection of the current regime-filtered validation design:

- too few regime-allowed dates per fold,
- too few OOS trades,
- no adjusted IC significance,
- weak mean OOS Sharpe.

The correct conclusion is:

- Promotable factors: 0
- Paper-ready factors: 0
- Diagnostic leads: 0 under the current regime-filtered setup

## Process Fix

Before any future ETF walk-forward run:

- Run ETF validation preflight first.
- Treat blocked preflight as a hard stop.
- Do not spend compute on a walk-forward config with insufficient regime-allowed rebalance dates.

## Next Direction

Round 28 should fix the validation path before mining more parameters:

1. Make ETF validation preflight respect `asset_universe_path` so its asset count and fold checks match the actual experiment universe.
2. Re-run preflight on a no-regime or less restrictive validation config.
3. If preflight clears, run walk-forward for the same frozen public trend-volume candidates without adding new parameters.

If the no-regime / less-restrictive walk-forward also rejects all candidates, rotate to a new public ETF factor family instead of continuing trend-volume mutations.
