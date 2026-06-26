# CN Stock Round304-309 Clean Pressure Review (2026-06-27)

Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Context

This review records the first post-audit 24h sprint batch after switching from short-window IC mining to full-sample clean portfolio diagnostics. CN stock research remains an auxiliary factor source for the broader project. The test standard is stricter than prior IC-only reports:

- 2015-01-01 to 2025-12-31 full sample.
- `close` is used for factor construction and backtest price where the diagnostic supports it.
- `CN_XBEI` is excluded.
- Assets with any `close` or `adj_close` daily return above 50% are quarantined.
- Costed long-only TopN diagnostics include 1-day execution lag, 20-day holding, 1m portfolio value, and 5% max participation.
- Raw total return is not enough. Extreme-trade-excluded return, drawdown, overlap-adjusted Sharpe, capacity, and yearly stability are required before promotion.

## Rounds

### Round304: Clean Technical Close Baseline

Report: `data/reports/round304_24h_profit_sprint_clean_technical_close_fast_screen_full2015_2025_20260627`

Scope: 11 representative technical factors, Top100, 10 bps, 20-day hold, 5-day rebalance.

Best raw case:

- `low_volatility_20_top100_hold20_reb5_cost10_cap1e+06`
- Total return: `+41.27%`
- Annualized return: `+1.64%`
- Sharpe: `0.225`
- Overlap-adjusted Sharpe: `0.121`
- Max drawdown: `-58.20%`
- Win rate: `48.46%`
- Extreme-excluded total return: `-4.54%`
- Diagnostic pass cases: `0 / 11`

Conclusion: traditional technical factors are not useful as direct long-only CN stock factors under clean `close` stress. The apparent low-volatility edge is not robust after removing extreme single-name returns.

### Round305: Daily-Basic Value/Quality Fast Screen

Report: `data/reports/round305_24h_profit_sprint_daily_basic_clean_fast_screen_full2015_2025_20260627`

Scope: 12 daily-basic/public value-quality-liquidity factors, Top100, 10 bps, 20-day hold, 5-day rebalance.

Best raw case:

- `daily_basic_value_yield_size_neutral_20_top100_hold20_reb5_cost10_cap1e+06`
- Total return: `+72.91%`
- Annualized return: `+2.56%`
- Sharpe: `0.320`
- Overlap-adjusted Sharpe: `0.172`
- Max drawdown: `-55.97%`
- Win rate: `47.98%`
- Extreme-excluded total return: `+3.90%`
- Extreme-excluded annualized return: `+0.18%`
- Diagnostic pass cases: `0 / 12`

Conclusion: daily-basic value/yield is the least bad direction so far because it remains slightly positive after extreme-trade exclusion, but the return is too small and drawdown too large. It is a weak research clue, not a tradable factor.

### Round306: Daily-Basic Top4 Parameter/Liquidity Tightening

Report: `data/reports/round306_24h_profit_sprint_daily_basic_clean_top4_grid_full2015_2025_20260627`

Scope: best four daily-basic candidates, Top50/100/200, 5/10 bps, 5/10-day rebalance, min signal amount raised to 50m.

Best raw case:

- `daily_basic_value_yield_size_neutral_20_top50_hold20_reb5_cost5_cap1e+06`
- Total return: `+44.97%`
- Annualized return: `+2.17%`
- Sharpe: `0.259`
- Overlap-adjusted Sharpe: `0.136`
- Max drawdown: `-56.95%`
- Win rate: `49.54%`
- Extreme-excluded total return: `-8.25%`
- Diagnostic pass cases: `0 / 48`

Conclusion: tighter liquidity and TopN grids did not rescue the line. The cleaner top-50 version loses money after extreme-trade exclusion.

### Round307-308: Daily-Basic Market-Regime Repair

Reports:

- `data/reports/round307_24h_profit_sprint_daily_basic_regime120_fast_screen_full2015_2025_20260627`
- `data/reports/round308_24h_profit_sprint_daily_basic_regime60_fast_screen_full2015_2025_20260627`

Scope: top four daily-basic factors with 120-day strict market regime and 60-day looser market regime.

Results:

- Strict 120-day regime left very few dates and produced negative returns.
- Looser 60-day regime also produced negative returns for all four candidates.
- Diagnostic pass cases: `0 / 8`

Conclusion: the daily-basic weakness is not fixed by a simple market-risk-on filter. The raw full-sample profit likely comes from crisis/rebound and extreme-name exposure rather than a stable regime-conditioned edge.

### Round309: Public Bar Indicator Families

Report: `data/reports/round309_24h_profit_sprint_bar_factor_clean_fast_screen_full2015_2025_20260627`

Scope: smart money, supertrend/OBV, liquidity shock recovery, information discreteness, and trend-strength state indicators.

Best raw case:

- `fip_discrete_jump_reversal_20_5_top100_hold20_reb5_cost10_cap1e+06`
- Total return: `+6.81%`
- Annualized return: `+0.31%`
- Sharpe: `0.082`
- Overlap-adjusted Sharpe: `0.049`
- Max drawdown: `-69.63%`
- Win rate: `45.68%`
- Extreme-excluded total return: `-40.52%`
- Diagnostic pass cases: `0 / 11`

Conclusion: public bar indicators did not produce a useful long-only factor. Smart-money and supertrend variants were materially negative in this CN stock universe under clean stress.

## Audit

No factor from Rounds304-309 is paper-ready or simulation-ready.

The best clue is still `daily_basic_value_yield_size_neutral_20`, but only as a weak component candidate:

- It has the best raw and extreme-excluded profile in the batch.
- Its overlap-adjusted Sharpe is far below threshold.
- Its drawdown is far beyond the user's stated tolerance around 30%.
- Tightening liquidity and adding simple market regime filters made it worse.

Stop rules now applied:

- Do not expand plain technical TopN grids.
- Do not expand smart-money/supertrend/OBV long-only grids unless the signal is redesigned, not merely retuned.
- Do not promote daily-basic value/yield directly.
- Any new candidate must beat the daily-basic value/yield clue on extreme-excluded return and drawdown, not just raw total return.

## Next Direction

The next work should move from single-factor ranking to portfolio construction and factor repair:

- Build a value/yield base plus explicit drawdown-risk penalty, using `daily_basic_value_yield_size_neutral_20` only as one component.
- Add crash-risk features before ranking, not as a post-hoc market filter.
- Test industry/size bucket neutrality and portfolio-level volatility targeting.
- Consider bottom-exclusion/avoidance factors separately, because many public indicators may be better at avoiding losers than selecting winners.
