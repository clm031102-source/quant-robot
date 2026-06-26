# CN Stock Round310-315 Turnover Low Review (2026-06-27)

Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Rounds304-309 showed that most clean full-sample factor families failed. This batch tested whether the earlier low-turnover line was merely a data artifact or still retained value under the stricter 24h sprint gates.

Common gates:

- Full sample: 2015-01-01 to 2025-12-31.
- `close` factor/backtest price.
- `CN_XBEI` excluded.
- Any asset with daily `close` or `adj_close` return above 50% quarantined.
- Costed long-only TopN portfolio, 1-day execution lag, 20-day holding, participation cap.
- Extreme-trade-excluded metrics audited.

## Round310: Value/Yield Risk Repair Failed

Report: `data/reports/round310_24h_profit_sprint_value_yield_risk_repair_fast_screen_full2015_2025_20260627`

New candidates:

- `daily_basic_value_yield_lowtail_guard_20`
- `daily_basic_value_yield_crash_penalty_60`
- `daily_basic_value_yield_liquid_defensive_20`
- `daily_basic_value_yield_balanced_repair_20`

Best case:

- `daily_basic_value_yield_balanced_repair_20_top100_hold20_reb5_cost10_cap1e+06`
- Total return: `-42.46%`
- Annualized return: `-2.89%`
- Max drawdown: `-78.92%`
- Diagnostic pass cases: `0 / 4`

Conclusion: the risk-repair formula removed the weak value/yield edge rather than stabilizing it.

## Round311: Raw Tushare Daily-Basic Re-Audit

Report: `data/reports/round311_24h_profit_sprint_raw_tushare_daily_basic_clean_fast_screen_full2015_2025_20260627`

Best case:

- `turnover_rate_low_top100_hold20_reb5_cost10_cap1e+06`
- Total return: `+103.90%`
- Annualized return: `+3.32%`
- Sharpe: `0.410`
- Overlap-adjusted Sharpe: `0.217`
- Max drawdown: `-52.65%`
- Win rate: `49.27%`
- Extreme-excluded total return: `+30.76%`
- Extreme-excluded annualized return: `+1.28%`
- Extreme-excluded Sharpe: `0.197`
- Capacity-limited trades: `0`

Conclusion: low turnover is not just an extreme-trade illusion. It remains the strongest clean full-sample clue so far, but drawdown and overlap-adjusted Sharpe still block promotion.

## Round312: Low-Turnover Parameter Grid

Report: `data/reports/round312_24h_profit_sprint_raw_turnover_low_grid_full2015_2025_20260627`

Best case:

- `turnover_rate_low_top50_hold20_reb5_cost5_cap1e+06`
- Total return: `+151.32%`
- Annualized return: `+5.73%`
- Sharpe: `0.614`
- Overlap-adjusted Sharpe: `0.319`
- Max drawdown: `-45.79%`
- Win rate: `50.24%`
- Extreme-excluded total return: `+59.21%`
- Extreme-excluded annualized return: `+2.91%`
- Extreme-excluded Sharpe: `0.369`
- Extreme-excluded max drawdown: `-49.18%`
- Losing years: `2`
- Yearly positive rate: `81.82%`
- Capacity-limited trades: `0`
- Diagnostic pass cases: `0 / 32`

Conclusion: Top50/5bps/5-day rebalance is the best research candidate in the sprint so far. It is still blocked by drawdown and overlap-adjusted Sharpe.

## Rounds313-314: Simple Market Regime Repair Failed

Reports:

- `data/reports/round313_24h_profit_sprint_turnover_low_regime_grid_full2015_2025_20260627`
- `data/reports/round314_24h_profit_sprint_turnover_low_regime60_full2015_2025_20260627`

Results:

- Strict 120-day risk-on regime turned the candidate negative.
- Looser 60-day regime also turned the candidate negative.

Conclusion: low-turnover returns are not fixed by a simple broad-market momentum filter. The signal may harvest weak-market/recovery behavior, so naive risk-on gating destroys the useful part.

## Round315: Exact Backtest Validation

Report: `data/reports/round315_24h_profit_sprint_turnover_low_exact_validation_20260627`

Exact engine result for `turnover_rate_low_top50_hold20_reb5_cost5_cap1e+06`:

- Factor rows after rebalance filter: `393,140`
- Trade rows: `26,423`
- Total return: `+150.58%`
- Annualized return: `+5.71%`
- Sharpe: `0.613`
- Overlap-adjusted Sharpe: `0.319`
- Max drawdown: `-45.91%`
- Win rate: `50.24%`
- Extreme-excluded total return: `+58.74%`
- Extreme-excluded annualized return: `+2.89%`
- Extreme-excluded Sharpe: `0.367`
- Extreme-excluded max drawdown: `-49.28%`
- Capacity-limited trades: `0`

Conclusion: the fast diagnostic was accurate. The candidate is real enough to keep researching, but not safe enough for paper/simulation promotion.

## Decision

Current best factor/parameter:

- Factor: `turnover_rate_low`
- TopN: `50`
- Cost: `5 bps`
- Holding: `20`
- Rebalance: `5`
- Execution lag: `1`
- Price: `close`
- Universe cleaning: exclude `CN_XBEI`, quarantine assets with any daily return above 50%

Status:

- Paper-ready: `0`
- Simulation-ready: `0`
- Strong research candidate: `1`

Next work should not broaden raw low-turnover grids. It should try drawdown-specific repairs:

- Market-neutral or industry/size-bucket low-turnover selection.
- Portfolio volatility targeting or cash overlay, evaluated as portfolio construction rather than factor promotion.
- Crash-exposure diagnostics for the exact 2015/2018/2022 drawdown periods.
- ETF translation check: whether CN stock low-turnover breadth can become a regime/breadth input for ETF rotation rather than a direct stock portfolio.
