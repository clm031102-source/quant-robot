# CN Stock Daily-Basic Free-Float Supply Quality Final-Holdout Audit Round145

- Date: 2026-06-22
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor mining, research-to-review only
- Candidate family: `daily_basic_free_float_supply_quality`
- Source line: Round140 event-adjusted clean preflight -> Round141 clean walk-forward candidate

## Objective

Round145 tested whether the frozen Round141 daily-basic free-float supply quality candidate still worked after a true 2026 final-holdout read. The goal was not to tune parameters. The goal was to verify whether an apparently clean preflight and aggregate walk-forward result survived a fresh, read-once holdout.

## Data Refresh

The first diagnostic run requested final holdout, but factor signals stopped at 2025-12-23 even though bars reached 2026-06-15. That meant the test had not truly read 2026 factor inputs.

I refreshed Tushare daily-basic inputs for 2026 into `data/processed/office_desktop_20260622_daily_basic_final_holdout_2026` and kept the output out of Git.

- Trade dates downloaded: 106
- Rows: 581,185
- Assets: 5,536
- Date range: 2026-01-05 to 2026-06-15
- Duplicate rows: 0
- Missing asset id rows: 0
- Missing numeric rows: 670,349
- Main missing numeric columns: `dv_ratio` 169,675, `dv_ttm` 187,183, `pe` 146,913, `pe_ttm` 161,186, `pb` 4,194

During refresh, Tushare intermittently returned an empty raw response for valid trade dates. Round145 added retry handling for transient empty daily-basic responses in `src/quant_robot/data/ingest/tushare_factor_inputs.py`.

## Readiness Result

After adding the 2026 daily-basic root, the final-holdout readiness audit cleared:

- Final holdout requested: true
- Final holdout start: 2026-01-01
- Max bar date: 2026-06-15
- Max signal date: 2026-05-28
- Signals cover final holdout: true
- Holdout fold rows: 6
- Walk-forward accepted candidates before holdout-result audit: 6
- Final holdout actually read: true

## Aggregate Result

The aggregate walk-forward leaderboard still looked acceptable on the surface:

- Case count: 6
- Fold count: 4
- Fold rows: 24
- Walk-forward accepted candidates: 6
- Best compounded test total return: 1.2822%
- Best mean test overlap-adjusted Sharpe: 1.0717
- Worst test max drawdown: -0.5895%
- Max extreme trade return count: 1
- Max capacity-limited trades: 0

This aggregate view is misleading because folds 2 and 3 offset a failed 2026 holdout fold.

## Final-Holdout Result

Round145 added `final_holdout_result_audit` to prevent aggregate acceptance from overriding a failed final holdout.

All 6 aggregate-accepted candidates failed the final holdout fold:

| Cost | Capital | Holdout Total Return | Holdout Annualized Return | Holdout Sharpe | Holdout Overlap Sharpe | Holdout Max DD | Win Rate | Trades | Extreme Trades |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 bps | 100,000 | -0.5949% | -1.4924% | -2.846 | -5.697 | -0.5697% | 40.0% | 300 | 1 |
| 10 bps | 500,000 | -0.5949% | -1.4924% | -2.846 | -5.697 | -0.5697% | 40.0% | 300 | 1 |
| 10 bps | 1,000,000 | -0.5949% | -1.4924% | -2.846 | -5.697 | -0.5697% | 40.0% | 300 | 1 |
| 20 bps | 100,000 | -0.6248% | -1.5670% | -2.923 | -5.785 | -0.5895% | 40.0% | 300 | 1 |
| 20 bps | 500,000 | -0.6248% | -1.5670% | -2.923 | -5.785 | -0.5895% | 40.0% | 300 | 1 |
| 20 bps | 1,000,000 | -0.6248% | -1.5670% | -2.923 | -5.785 | -0.5895% | 40.0% | 300 | 1 |

Common holdout blockers:

- `overlap_adjusted_sharpe_below_min`
- `extreme_trade_return_present`
- `oos_non_positive_total_return_after_cost`
- `oos_non_positive_annualized_return_after_cost`
- `oos_overlap_adjusted_sharpe_below_min`
- `test_total_return_below_minimum`
- `test_overlap_adjusted_sharpe_below_minimum`

## Decision

- Paper gate allowed: false
- Promotion allowed: false
- Holdout passed cases: 0
- Next direction: `hibernate_or_rotate_after_final_holdout_failure`

This is not a drawdown-tolerance issue. The failed holdout has negative return, negative annualized return, negative Sharpe, negative overlap-adjusted Sharpe, 40% win rate, and a remaining extreme-trade blocker. A user willingness to accept a 30% drawdown does not convert this into a promotable factor because the final holdout did not earn money after cost.

## Engineering Outcome

Reusable improvements added in Round145:

- `src/quant_robot/ops/final_holdout_readiness_audit.py`
- `scripts/run_final_holdout_readiness_audit.py`
- `src/quant_robot/ops/final_holdout_result_audit.py`
- `scripts/run_final_holdout_result_audit.py`
- Tushare daily-basic transient-empty retry logic in `src/quant_robot/data/ingest/tushare_factor_inputs.py`
- Unit tests for readiness audit, result audit, CLI behavior, and ingest retry behavior

## Method Lesson

Aggregate walk-forward acceptance is not enough. A candidate may pass earlier OOS folds and still fail the read-once final holdout. From the next round onward, promotion review must require:

1. Final-holdout readiness audit proves bars, factor signals, and chronological test folds touch the holdout window.
2. Final-holdout result audit proves at least one aggregate-accepted case also passes the holdout fold.
3. No tuning is allowed after reading the final holdout.
4. If all holdout cases fail, hibernate the family or rotate to a different economic thesis instead of expanding parameters.

