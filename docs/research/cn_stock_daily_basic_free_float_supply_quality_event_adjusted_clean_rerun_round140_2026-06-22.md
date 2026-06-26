# CN Stock Daily-Basic Free-Float Supply Quality Event-Adjusted Clean Rerun - Round140

Date: 2026-06-22

Stage: `daily_basic_free_float_supply_quality_event_adjusted_clean_rerun`

Source: Round139 true-close extreme trade liquidity/limit audit.

Output:

- JSON: `data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_round140_20260622/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.json`
- CSV: `data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_round140_20260622/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_leaderboard.csv`
- Markdown: `data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_round140_20260622/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.md`

## Objective

Round139 showed that the 156 true-close extreme trade rows were only 15 unique trade paths, with 11 no-obvious-blocker paths and 4 blocked paths. Round140 tests whether the same frozen daily-basic free-float supply quality residual signal still has evidence after all 15 audited event paths are removed from the signal matrix.

This is a clean rerun, not a parameter search.

## Method

- Rebuilt the same Round138/Round139 strict-clean residual factor.
- Kept the long-cycle window closed at 2015-01-01 through 2025-12-31.
- Kept final holdout closed.
- Kept the same portfolio settings: top100, hold20, rebalance20, lag1, cost 10/20 bps, capital 100k/500k/1m, market impact 10 bps, max participation 1%.
- Removed all Round139 audited event paths at the signal-date/asset level before portfolio construction.
- Reran the same cost/capacity/stress-guard preflight grid.

## Results

- Requested event paths: 15.
- Matched event paths: 15.
- Excluded factor rows: 15.
- Remaining factor rows: 2,169,577.
- True-close extreme trades after adjustment: 0.
- Phantom-alpha trades after adjustment: 0.
- Walk-forward allowed case count: 6.
- Promoted factors: 0.

Best allowed case:

| Metric | Value |
|---|---:|
| Case | `block_stress_rebalance_dates_top100_hold20_reb20_lag1_cost10_cap100000` |
| Total return | 21.31% |
| Annualized return | 18.99% |
| Sharpe | 0.820 |
| Overlap-adjusted Sharpe | 1.043 |
| Max drawdown | -16.37% |
| Win rate | 50.00% |
| OOS/test total return | 18.99% |
| OOS/test Sharpe | 2.913 |
| OOS/test overlap-adjusted Sharpe | 5.165 |
| OOS/test max drawdown | -1.62% |
| OOS/test win rate | 83.33% |
| Extreme trade count | 0 |

Allowed cases are all `block_stress_rebalance_dates` variants across 10/20 bps and 100k/500k/1m capital. The unguarded `none` variants remain blocked by low overlap-adjusted Sharpe, calendar holding gate filtered trades, and max drawdown below the user's soft floor.

## Interpretation

Round140 is the first useful positive evidence after the price-basis and extreme-trade cleanup. The result no longer depends on the 15 audited event paths, and the post-adjustment extreme trade count is zero.

However, it is still not promotable. The allowed cases are stress-guard dependent and come from a preflight grid, not a rolling clean walk-forward validation. The OOS/test metrics are strong but may be sample-sensitive; they must not be treated as final proof.

## Decision

Promotion: `0`.

Research lead: yes.

Next direction:

`round141_daily_basic_free_float_supply_quality_clean_walk_forward_after_event_adjustment`

Required before promotion:

- Run clean walk-forward after event adjustment.
- Confirm accepted fold count and regime coverage.
- Check whether the stress guard is genuinely ex-ante and not just a drawdown rescue.
- Keep final holdout closed.
- Keep event-path exclusion fixed; do not tune exclusions after seeing results.

