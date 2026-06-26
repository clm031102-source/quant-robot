# CN Stock Factor Mining Work Report Rounds 1-85 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha, not ETF rotation
- Safety: research-to-review only

Headline status through Round85:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Round85 newly useful infrastructure: signal-date liquidity gate and calendar-holding gate in the core backtest path
- Next direction: `round86_capacity_safe_public_quality_value_momentum_composite`

The important outcome is not a factor promotion. It is that the previous best-looking low-turnover line was re-tested with tradeability gates and mostly collapsed.

## Best Historical Evidence So Far

| Area | Bright Data | Final Status |
|---|---|---|
| RSI/Bollinger technical baselines | RankIC about 0.047-0.049 | rejected for drawdown/tail/capacity weakness |
| Data repair | false +91.71x return collapsed to +2.36x after adjusted-ratio repair | fake alpha correctly killed |
| Public price-volume formulas | `formula_pv_corr_reversal_20` RankIC about 0.076, t=10.88 | portfolio translation failed |
| Industry-neutral formula replay | neutral RankIC about 0.088-0.091, t near 49 | strong IC, weak portfolio Sharpe |
| Bottom-exclusion overlays | overlay t up to 8.46, positive rate about 70% | costed portfolios failed drawdown/Sharpe |
| Daily-basic residuals | neutral RankIC 0.042-0.056 | long-only conversion failed |
| Benchmark beta diagnostics | residual alpha t=4.39-5.42 | beta dominance too high |
| RSRS public indicator | `rsrs_reversal_18_60` total +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| SuperTrend public indicator | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Daily-basic low turnover raw | total return above +5000%, overlap Sharpe near 0.9-1.0 | rejected by Round84/85 tradeability checks |

## Round85 Result

Round85 replayed the two low-turnover leads with:

- signal-date amount >= 10,000,000 before TopN selection;
- calendar holding <= 60 days;
- 1% ADV participation gate;
- 10 bps cost and 20 bps market-impact model;
- same 2015-2025 full sample and frozen Top100/20-bar/5-bar rebalance parameters.

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Relative Return | Calendar-Limited | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | +177.86% | 6.02% | 0.755 | 0.410 | -34.63% | -2195.89% | 205 | 1 | rejected |
| `turnover_rate_f_low` | +130.86% | 4.62% | 0.582 | 0.294 | -44.97% | -2242.88% | 332 | 1 | rejected |

Compared with Round83:

| Factor | Round83 Raw Total | Round85 Clean Total | Change |
|---|---:|---:|---|
| `turnover_rate_low` | +5127.61% | +177.86% | raw return engine mostly removed |
| `turnover_rate_f_low` | +5318.72% | +130.86% | raw return engine mostly removed |

The IC stayed strong, but the portfolio was not tradable enough:

- `turnover_rate_low` RankIC 0.1028, t=13.61, but overlap Sharpe only 0.410.
- `turnover_rate_f_low` RankIC 0.1079, t=15.72, but overlap Sharpe only 0.294.
- Tail RankIC was weak for both.
- Both underperformed the equal-weight CN stock benchmark badly.

## What Was Built

Reusable project improvements:

- Core backtest now supports `min_signal_amount` before TopN selection.
- Core backtest now supports `max_calendar_holding_days` as a conservative execution-validity gate.
- Research pipeline, experiment grid, CLI, and extreme-trade diagnostic now pass these gates.
- Leaderboards now surface:
  - `signals_filtered_min_signal_amount`
  - `calendar_limited_trades`
  - `max_calendar_holding_days`
  - `p99_calendar_holding_days`
  - `max_skipped_calendar_holding_days`
- Decision summary rejects calendar-limited cases.

## Current Conclusion

The project has found information, but not yet a deployable A-share stock factor.

The clearest lesson is that positive RankIC is not enough. Low-turnover has cross-sectional information, but the tradable long-only TopN conversion fails once liquidity and calendar realism are enforced.

The low-turnover direct line is now hibernated. The next work should rotate to a publicly grounded, capacity-safe composite family instead of continuing to tune low-turnover parameters.
