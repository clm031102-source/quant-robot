# CN Stock Round322-324 Turnover Overlay Decision-Date Audit (2026-06-27)

Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round320-321 suggested that adding a lagged market-state exposure cap to the `turnover_rate_low` entry-cash pipeline could materially improve Sharpe and reduce drawdown. This audit fixed the weakest implementation point: the period-return file only had exit dates, so market-state overlays could be accidentally aligned to the date when profit was realized instead of the date when exposure was decided.

The corrected pipeline now writes `signal_date`, `entry_date`, and `date` for every period-return row. Market-state caps are aligned by decision date before walk-forward scoring.

## Round322: Rebuilt Tradeability Period Returns

Report:

`data/reports/round322_24h_profit_sprint_turnover_low_tradeability_exposure_decision_date_20260627`

Setup:

- Full sample: 2015-01-01 to 2025-12-31.
- `turnover_rate_low`, Top50.
- `close` factor and backtest price.
- Exclude `CN_XBEI`.
- Quarantine assets with any daily `close` or `adj_close` return above 50%.
- 1-day execution lag, 20-day holding, 5-day rebalance, 5 bps cost.
- Portfolio value: 1,000,000.

Rebuilt baseline:

- Raw total return: `+151.32%`
- Raw annualized return: `+5.73%`
- Raw Sharpe: `0.614`
- Raw overlap-adjusted Sharpe: `0.319`
- Raw max drawdown: `-45.79%`
- Entry-cash annualized return: `+4.51%`
- Entry-cash Sharpe: `0.644`
- Entry-cash overlap-adjusted Sharpe: `0.355`
- Entry-cash max drawdown: `-35.63%`

Tradeability:

- Entry-blocked trades: `5,609 / 26,450` (`21.21%`)
- Exit-blocked trades: `5,638 / 26,450` (`21.32%`)
- Roundtrip-blocked trades: `5,797 / 26,450` (`21.92%`)
- Extreme trade count above 50% gross return: `163`

Decision-date repair:

- `turnover_low_period_returns.csv` now contains `signal_date`, `entry_date`, `date`, `signal_date_count`, and `entry_date_count`.
- This allows overlays to use information available at decision time rather than exit time.

## Round323: Reusable Market-State WF, Entry-Date Alignment

Report:

`data/reports/round323_24h_profit_sprint_turnover_low_market_state_overlay_wf_reusable_20260627`

Market state:

- Source: clean-universe median daily close return.
- Date range: 2015-01-06 to 2025-12-31.
- Caps generated from lagged market equity state.
- Grid: lookbacks `60/120/180`, momentum thresholds `0/-5%`, drawdown threshold `-10%`, cap exposure `50%/25%`.
- Decision date: `entry_date`.
- Policies tested: `18`.
- Folds: `7`, with 3-year train, 1-year test, 1-year step.

Best fixed policy after correct alignment:

- Policy: `entry_cash_dd_warn15_cut25`
- Average test annualized return: `+5.33%`
- Average test Sharpe: `0.671`
- Average test overlap-adjusted Sharpe: `0.404`
- Worst test drawdown: `-17.44%`
- Positive test rate: `85.71%`
- Strict pass rate: `85.71%`

Best market-state policies did reduce drawdown but cut too much return:

- `dd15_cut25_market_lb180_mom0_dd0p1_cap0p5`: average test annualized return `+2.53%`, overlap Sharpe `0.364`, worst drawdown `-10.85%`.
- `dd15_cut25_market_lb180_mom0_dd0p1_cap0p25`: average test annualized return `+1.26%`, overlap Sharpe `0.364`, worst drawdown `-5.57%`.

Selected-by-train result:

- Average test annualized return: `+3.52%`
- Average test Sharpe: `0.647`
- Average test overlap-adjusted Sharpe: `0.332`
- Worst test drawdown: `-12.03%`
- Positive test rate: `85.71%`
- Strict pass rate: `71.43%`

The 2018 fold still failed:

- Test window: 2018-02-09 to 2019-02-08.
- Selected policy: `dd15_cut25_market_lb120_mom0_dd0p1_cap0p25`.
- Annualized return: `-2.89%`
- Sharpe: `-2.370`
- Overlap-adjusted Sharpe: `-2.174`
- Max drawdown: `-5.57%`

## Round324: More Conservative Signal-Date Alignment

Report:

`data/reports/round324_24h_profit_sprint_turnover_low_market_state_overlay_wf_signal_date_20260627`

Signal-date alignment produced the same high-level conclusion:

- Best fixed policy remained `entry_cash_dd_warn15_cut25`.
- Average test annualized return stayed `+5.33%`.
- Average test overlap-adjusted Sharpe stayed `0.404`.
- Market-state policies reduced drawdown but were not superior on return or overlap-adjusted Sharpe.
- Selected-by-train average annualized return was `+5.44%`, but selected overlap-adjusted Sharpe was only `0.332` and strict pass rate was `71.43%`.

## Audit Conclusion

The earlier Round320-321 market-state improvement should be treated as optimistic and not reusable evidence. After the period-return file was fixed to carry decision dates, the market-state cap no longer dominates the simple drawdown overlay. The likely issue was date alignment: using exit-date period returns without a decision-date column can accidentally let a risk overlay react too late or too favorably relative to the actual trade decision.

Current best reusable candidate remains:

- `turnover_rate_low`
- Entry-blocked trades treated as cash.
- Drawdown overlay: warn at `-15%`, cut at `-25%`.
- Top50, hold20, rebalance5, cost5 bps.

Status:

- Simulation-ready factors: `0`
- Paper-ready factors: `0`
- Best research candidate: `turnover_rate_low + entry_cash + dd_warn15_cut25`
- Market-state cap: keep as a drawdown-control diagnostic, not as the primary candidate.

## Direction Change

Do not spend more rounds widening the low-turnover market-state cap grid unless there is a new economic reason. The next factor-mining work should change family and test public, economically motivated indicators, especially:

- Price-volume reversal / failure-reversal after stress.
- Supertrend or trend-state failure signals, already present in public technical modules.
- Smart-money style proxies that use amount/volume behavior without relying only on Tushare moneyflow.
- Industry-neutral and size/liquidity-neutral variants to avoid small-cap or stale-trading artifacts.

The next three-round block should produce a factor-family comparison, not another low-turnover parameter expansion.
