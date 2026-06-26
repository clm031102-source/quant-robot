# CN Stock Round331-333 Three-Round Audit

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock factor validation.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Rounds Covered

| Round | Purpose | Decision |
|---|---|---|
| 331 | Fixed ex-ante market-state cap | Useful risk control, but over-blocking |
| 332 | Stricter market-stress cap | Full-sample strong, walk-forward not confirmed |
| 333 | Low-turnover failure attribution | Found a cleaner repair candidate |

## What Worked

The best new result is not a market timing rule. It is a portfolio-internal cash-exclusion rule:

`cash_low_turnover_f_bottom20`

Applied to the current low-turnover lead:

`turnover_rate_low_top50_hold20_reb5_cost5`

This rule sends entry-allowed trades in the bottom 20% of `turnover_rate_f` within each signal-date portfolio to cash.

Evidence:

- Full-sample total return: +107.79% versus +107.64% benchmark.
- Annualized return: +4.52% versus +4.51%.
- Sharpe: 0.750 versus 0.644.
- Overlap-adjusted Sharpe: 0.414 versus 0.355.
- Max drawdown: -28.01% versus -35.63%.
- Cross-split mean OOS overlap Sharpe: 0.655 versus 0.561.
- Cross-split worst OOS drawdown: -16.75% versus -20.59%.

## What Failed

Market-state caps:

- Reduced 2017-2018 drawdown.
- But `momentum <= 0 OR drawdown <= -10%` capped 92%-97% of decisions.
- Stricter 60-day caps looked excellent full-sample, but walk-forward preferred the no-overlay benchmark in every split.
- Conclusion: market-state caps are a risk-control backup, not the next profit-factor path.

## Why The New Candidate Is Better

The `turnover_rate_f` exclusion is closer to the stock-selection mechanism:

- It is measured inside selected low-turnover trades, not at the broad-market level.
- It targets a plausible stale-liquidity/value-trap pocket.
- It was discovered from entry-allowed trades, so it is not just removing trades that were already unbuyable.
- It improves drawdown without destroying annualized return.

## Promotion Stance

Still blocked:

- Simulation-ready: 0
- Paper-ready: 0

Active research candidates:

1. `turnover_rate_low + entry-cash + cash_low_turnover_f_bottom20`
2. `turnover_rate_low + entry-cash + vol_target_5_lb84`
3. `turnover_rate_low + entry-cash + vol_target_4_lb168`

The first candidate now has the highest priority because it improves the stock-selection failure pocket before applying portfolio-level volatility control.

## Direction Adjustment

Stop:

- Broad market-state cap tuning.
- Public indicator re-runs that already failed residual or dedup gates.
- Same-family low-turnover TopN/cost parameter sweeps.

Start:

- Formal exact diagnostic for `cash_low_turnover_f_bottom20`.
- Compare fixed cash-exclusion versus fixed vol-target wrappers.
- Only test a combined cash-exclusion + vol-target wrapper after the exact diagnostic confirms the cash-exclusion rule survives.
