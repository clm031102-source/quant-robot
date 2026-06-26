# CN Stock Factor Mining Work Report Rounds 1-84 - 2026-06-21

## Executive Summary

This report updates the office-desktop CN stock factor-mining work through Round84.

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha, not CN ETF rotation
- Safety: research-to-review only; no broker/account/order/live-trading actions

Headline result:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Diagnostic-only raw low-turnover leads after Round84: 0
- Useful infrastructure added this round: capacity/extreme/calendar-holding trade diagnostic
- Next direction: `round85_calendar_holding_liquidity_gate_replay`

The most important Round84 conclusion is that the strongest Round83 returns were not usable alpha. They were contaminated by capacity breaches, sparse-trading calendar drift, and extreme single-name returns.

## What Round84 Changed

Round83 surfaced the brightest long-cycle raw numbers so far:

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | RankIC | IC t | Relative Return | Capacity-Limited | Extreme Flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | +5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% | 0.1028 | 14.99 | +2753.86% | 1,437 | true |
| `turnover_rate_f_low` | +5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% | 0.1079 | 17.03 | +2944.97% | 1,641 | true |

Round84 audited them with frozen parameters:

| Factor | Trades | Capacity-Limited | Extreme > 5x | Max Participation | Max Calendar Holding | P99 Calendar Holding | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | 46,437 | 1,437 | 19 | 166.67x ADV | 787 days | 39 days | rejected |
| `turnover_rate_f_low` | 43,202 | 1,641 | 19 | 8.80x ADV | 787 days | 42 days | rejected |

This kills the raw low-turnover direct-promotion line. The signal may still contain information, but not in its current tradable form.

## Past Work Results And Bright Data

The project has repeatedly found ranking information, especially in bottom-tail avoidance, but it has not yet converted that information into a robust tradable long-only stock strategy.

| Area | Bright Data | Outcome |
|---|---|---|
| Public technical baselines | RSI/Bollinger mean-reversion RankIC around 0.047-0.049 | rejected for drawdown/tail/capacity weakness |
| Data repair rounds | A false +91.71 return collapsed to +2.36 after adjusted-ratio repair | fake alpha killed correctly |
| Public price-volume formulas | `formula_pv_corr_reversal_20` RankIC around 0.076, t=10.88 | portfolio translation failed |
| Industry-neutral formula replay | neutral RankIC around 0.088-0.091, t near 49 | strong IC, weak portfolio Sharpe |
| Bottom-exclusion overlays | overlay t up to 8.46, positive rate about 70% | costed portfolios failed drawdown/Sharpe |
| Daily-basic residuals | neutral RankIC 0.042-0.056 | long-only conversion failed |
| Benchmark beta diagnostics | residual alpha t=4.39-5.42 | beta dominance too high |
| RSRS public indicator | `rsrs_reversal_18_60` total +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| SuperTrend public indicator | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Daily-basic low turnover | raw total return above +5000%, overlap Sharpe near 0.9-1.0 | rejected by Round84 capacity/calendar/extreme diagnostic |

## Why The Results Are Still Poor

The failure is not that every idea has zero information. The failure is that most information found so far does not survive the hard gates that matter for deployment:

- IC exists but portfolio construction loses it.
- Loser-avoidance signals improve relative behavior but do not produce acceptable absolute risk.
- Public formula families fail costed walk-forward after a promising full-sample or diagnostic result.
- Raw low-turnover signals harvest illiquidity and sparse trading, not clean tradable return.
- Naive Sharpe is consistently too generous; overlap-adjusted Sharpe is much lower.
- Capacity and calendar-holding problems were not visible enough until Round84's diagnostic was added.

## Useful Engineering Output

Reusable pieces now in the project:

- CN stock startup gate and direction governance.
- Three-round review and ten-round GitHub sync cadence.
- Long-cycle authority data config for 2015-2025.
- Daily-basic, moneyflow, public technical, RSRS, SuperTrend, and composite factor families.
- Authority config support in the research loader.
- Precomputed factor-matrix reuse for large grids.
- Data manifest with adjusted-ratio and source-root checks.
- IC-to-portfolio gap audit.
- Industry-neutral IC audit.
- Bottom-exclusion overlay and costed walk-forward tools.
- Benchmark beta and beta-hedged spread diagnostics.
- Enhanced extreme/capacity/calendar-holding trade diagnostic from Round84.

## Current Conclusion

As of Round84, the project has produced strong research evidence but no deployable factor.

The most valuable work this round is not a profitable factor; it is the discovery of a hidden process flaw:

> For sparse-trading stocks, a nominal 20-bar holding period can become hundreds of calendar days. Low-turnover factors exploit exactly those names, so raw low-turnover backtests are structurally suspect until calendar-holding and liquidity gates are enforced before selection.

Next work must therefore improve the backtest process before more factor mining:

`round85_calendar_holding_liquidity_gate_replay`

Stop doing:

- raw low-turnover TopN/window tuning;
- low-turnover promotion claims;
- more daily-basic sweeps before the calendar/entry-liquidity gate exists.

Continue doing:

- capacity-clean replay;
- calendar-holding drift gate;
- liquidity universe gate before selection;
- only then walk-forward validation.
