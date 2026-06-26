# CN Stock Round316-321 Turnover Tradeability Overlay Review (2026-06-27)

Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round315 confirmed that raw `turnover_rate_low_top50_hold20_reb5_cost5` was the strongest full-sample CN stock clue so far, but it still failed promotion because max drawdown was too high and overlap-adjusted Sharpe was weak.

This three-round review tested whether the issue was a bad factor formula or an execution/portfolio-construction problem.

Common setup:

- Full sample: 2015-01-01 to 2025-12-31.
- `close` factor and backtest price.
- Exclude `CN_XBEI`.
- Quarantine assets with any daily `close` or `adj_close` return above 50%.
- 1-day execution lag, 20-day holding, 5-day rebalance, 5 bps baseline cost.

## Round316: Liquid/Size Bucket Low-Turnover Repair Failed

Report:

`data/reports/round316_24h_profit_sprint_turnover_low_liquid_mv_bucket_full2015_2025_20260627`

Tested candidates:

- `turnover_rate_low_liquid_mv_bucket_rank`
- `turnover_rate_f_low_liquid_mv_bucket_rank`
- `turnover_rate_low_adv_blend_mv_bucket_rank`
- `turnover_rate_f_low_adv_blend_mv_bucket_rank`

Best case:

- `turnover_rate_low_adv_blend_mv_bucket_rank_top100_hold20_reb5_cost5_cap1e+06`
- Total return: `+59.05%`
- Annualized return: `+2.22%`
- Sharpe: `0.267`
- Overlap-adjusted Sharpe: `0.147`
- Max drawdown: `-58.35%`
- Extreme-excluded total return: `-19.49%`
- Diagnostic pass cases: `0 / 24`

Decision: the bucket/liquidity formula repair weakens the original low-turnover edge and does not solve drawdown. Do not continue expanding this grid without a new hypothesis.

## Round317: Tradeability Exposure Diagnostic

Report:

`data/reports/round317_24h_profit_sprint_turnover_low_tradeability_exposure_20260627`

Baseline exact reconstruction:

- Total return: `+151.32%`
- Annualized return: `+5.73%`
- Sharpe: `0.614`
- Overlap-adjusted Sharpe: `0.319`
- Max drawdown: `-45.79%`

Real A-share tradeability exposure:

- Entry-blocked trades: `5,609 / 26,450` (`21.21%`)
- Exit-blocked trades: `5,638 / 26,450` (`21.32%`)
- Roundtrip-blocked trades: `5,797 / 26,450` (`21.92%`)
- Top blocked reasons: `st_flag`, `delisted_or_inactive_flag`, `board_permission_blocked`, `limit_down_official`, `limit_up_official`

Cash-proxy stress:

- Entry-blocked-as-cash total return: `+107.64%`
- Entry-blocked-as-cash annualized return: `+4.51%`
- Entry-blocked-as-cash Sharpe: `0.644`
- Entry-blocked-as-cash overlap-adjusted Sharpe: `0.355`
- Entry-blocked-as-cash max drawdown: `-35.63%`

This is the key result: the low-turnover line is not just a formula problem. A large part of the drawdown and implementation risk comes from real tradeability constraints.

## Round318: Strategy-Level Risk Overlay Screen

Report:

`data/reports/round318_24h_profit_sprint_turnover_low_tradeability_overlay_20260627`

Best more-realistic line:

- Policy: `entry_cash_dd_overlay_warn10%_cut20%`
- Total return: `+91.03%`
- Annualized return: `+3.99%`
- Sharpe: `0.783`
- Overlap-adjusted Sharpe: `0.408`
- Max drawdown: `-22.55%`
- Average exposure: `58.69%`
- Minimum exposure: `25.00%`

Interpretation:

- This is not a new alpha factor. It is a portfolio/execution repair around the current strongest factor clue.
- The result is promising because drawdown moves into the user's acceptable range while total return remains positive.
- It is still not promotion-ready because the overlay was evaluated on the same full sample and overlap-adjusted Sharpe remains below the strict `0.50` gate.

## Round319: Calendar Walk-Forward Overlay Check

Reports:

- `data/reports/round319b_24h_profit_sprint_turnover_low_entry_cash_overlay_calendar_walk_forward_20260627`
- `data/reports/round319c_24h_profit_sprint_turnover_low_entry_cash_overlay_calendar_walk_forward_cli_20260627`

The reusable CLI path consumes:

`data/reports/round317_24h_profit_sprint_turnover_low_tradeability_exposure_20260627/turnover_low_period_returns.csv`

Calendar split:

- 3-year train.
- 1-year test.
- 1-year step.
- Input return series: `entry_cash_proxy_return`.
- Policy set fixed before testing: no overlay, three drawdown overlays, two volatility targets.

Best fixed policy:

- Policy: `entry_cash_dd_warn15_cut25`
- Test folds: `7`
- Positive test rate: `85.71%`
- Loose pass rate: `85.71%`
- Strict pass rate: `85.71%`
- Average test annualized return: `+5.33%`
- Average test Sharpe: `0.671`
- Average test overlap-adjusted Sharpe: `0.404`
- Worst test max drawdown: `-17.44%`

Important failure:

- 2018-02-09 to 2019-02-08 remained negative.
- Test annualized return: `-9.99%`
- Test Sharpe: `-2.49`
- Test overlap-adjusted Sharpe: `-1.89`
- Test max drawdown: `-17.44%`

Interpretation:

- This is the first line in the 24h sprint with meaningful out-of-sample evidence after realistic entry-tradeability cash handling.
- It is still not paper-ready because the 2018 bear/stress window fails, and selected-by-train policy choice underperforms the best fixed policy.
- The right next step is not a wider factor grid. It is a market-state repair focused on 2018-style stress while preserving 2019-2025 performance.

## Round320: Market-State Cap Screen

Report:

`data/reports/round320_24h_profit_sprint_turnover_low_market_state_overlay_20260627`

Candidate idea:

- Keep `entry_cash_dd_warn15_cut25`.
- Add a market-state exposure cap using only lagged clean-universe market information.
- Market state is based on median daily return equity, lagged by one day.
- Small fixed screen only: lookbacks 60/120/180, momentum thresholds 0 and -5%, cap 50% or 25%.

Best full-sample screen:

- Policy: `dd15_cut25_market_lb60_mom0_dd10_cap25`
- Total return: `+169.09%`
- Annualized return: `+6.16%`
- Sharpe: `1.411`
- Overlap-adjusted Sharpe: `0.668`
- Max drawdown: `-7.90%`
- Average exposure: `42.87%`

Best walk-forward summary in this fixed screen:

- Policy: `dd15_cut25_market_lb60_mom_neg5_dd10_cap25`
- Folds: `7`
- Average test annualized return: `+5.47%`
- Average test Sharpe: `1.321`
- Average test overlap-adjusted Sharpe: `0.729`
- Worst test drawdown: `-6.30%`
- Positive test rate: `85.71%`
- Strict pass rate: `85.71%`

Important caveat:

- The best policy was selected after viewing the screen, so this is not final evidence. It required nested policy selection.

## Round321: Nested Market-State Policy Selection

Report:

`data/reports/round321_24h_profit_sprint_turnover_low_market_state_nested_walk_forward_20260627`

Nested selection result:

- Folds: `7`
- Policies in candidate set: `13`
- Training-selected policies:
  - `dd15_cut25_market_lb60_mom0_dd10_cap0.25`: `6 / 7`
  - `dd15_cut25_market_lb60_mom-0.05_dd10_cap0.25`: `1 / 7`
- Average test annualized return: `+5.27%`
- Average test Sharpe: `1.279`
- Average test overlap-adjusted Sharpe: `0.698`
- Worst test max drawdown: `-6.40%`
- Positive test rate: `85.71%`
- Loose pass rate: `85.71%`
- Strict pass rate: `85.71%`

Remaining failure:

- 2018 remains negative, but the loss is reduced to about `-2.82%` annualized with max drawdown about `-6.40%`.
- This is acceptable as a stress-control improvement, but it is not proof of standalone alpha.

Interpretation:

- The most promising object is now a research pipeline: `turnover_rate_low` signal + entry-tradeability cash handling + drawdown risk budget + lagged market-state exposure cap.
- This is closer to a deployable portfolio rule than a pure factor formula.
- It must still pass a cleaner holdout and final anti-overfit review.

## Decision

Current status:

- Paper-ready factors: `0`
- Simulation-ready factors: `0`
- Direct factor formula to keep: `turnover_rate_low`
- Best actionable research candidate: `turnover_rate_low` with entry-tradeability cash handling, fixed drawdown risk budget, and lagged market-state exposure cap

Direction change:

- Stop widening low-turnover bucket formula grids.
- Continue with tradeability-aware portfolio validation, not raw factor formula mutation.
- Next required check: walk-forward validation of the entry-cash drawdown overlay and parameter sensitivity around warning/cut thresholds.

## Next Work

Round322 should avoid new formula mining and instead tighten validation:

- Convert the market-state cap into a reusable project entrypoint.
- Re-run with a final holdout if 2026 aligned bars and daily-basic inputs are available.
- Add sensitivity checks around the selected 60-day state cap.
- Keep paper/simulation promotion blocked until holdout, overfit, and tradeability-delay checks are complete.
