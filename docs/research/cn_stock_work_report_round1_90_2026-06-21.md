# CN Stock Factor Mining Work Report Rounds 1-90 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round90:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current factor candidates ready for backtest: 0
- Current useful capability: real Tushare `fina_indicator` symbol-scoped smoke passed PIT readiness
- Current next direction: `round91_tushare_fina_indicator_long_history_backfill_plan`

The project still has no deployable factor. The important progress since Round88 is that the missing data-layer problem has been attacked directly: the project can now ingest real Tushare financial indicator rows with announcement dates and pass a PIT readiness gate.

## Rounds 87-90 Completed

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 87 | Public QVM bottom-exclusion walk-forward | two frozen QVM leads both accepted 0/7 folds | QVM hibernated |
| 88 | Tushare financial PIT readiness audit | 6,939 existing files scanned, 0 financial-like datasets | profitability mining blocked |
| 89 | `fina_indicator` fixture ingestion smoke | fixture processed 4 rows, 2 assets, 2 quarters; readiness passed | PIT data shape proven |
| 90 | Real Tushare `fina_indicator` smoke | `000001.SZ:20240331` processed 1 real row; readiness passed | real schema path proven |

## Bright Data Worth Remembering

| Area | Bright Data | Final Status |
|---|---|---|
| Low-turnover raw | `turnover_rate_low` +5127.61%, Sharpe 1.983 | rejected as capacity/calendar contaminated |
| Low-turnover raw | `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | rejected as capacity/calendar contaminated |
| Capacity-clean low-turnover | +177.86% / +130.86% clean total return | rejected, overlap Sharpe only 0.410 / 0.294 |
| RSRS | `rsrs_reversal_18_60` +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| SuperTrend | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Public QVM direct | RankIC 0.0724, t=9.43, capacity-limited trades 0 | rejected, overlap Sharpe 0.226 and max DD -47.71% |
| Public QVM exclusion | mean relative +1.07% / +0.69%, capacity-limited trades 0 | rejected, accepted folds 0/7 |
| Financial data layer | real `fina_indicator` row has `ann_date`, `end_date`, ROE, margins/growth/cash-flow fields | data capability accepted, not a factor yet |

## Why There Is Still No Useful Factor

The validation stack is filtering aggressively:

- positive IC did not become a robust costed long-only portfolio;
- high raw returns were often illiquidity, capacity, or stale-holding artifacts;
- public technical indicators were more useful for loser avoidance than buy signals;
- daily-basic proxies were not true profitability data;
- true profitability factors could not be tested until PIT financial data existed.

## Current Conclusion

As of Round90, the factor count that matters remains:

- Usable factors: 0
- Promotable factors: 0
- Paper-ready factors: 0

But the project is now moving in the correct direction. The next bottleneck is no longer "which proxy formula to tune"; it is building a long-history PIT financial indicator dataset that can support real profitability-quality hypotheses.

## Next Action

Round91 should produce a safe long-history backfill plan for `fina_indicator`:

- quarterly periods from 2015-03-31 to 2025-12-31;
- symbol universe and batching policy;
- resume and rate-limit controls;
- no token leakage;
- no committed data;
- readiness audit before any profitability factor pre-registration.
