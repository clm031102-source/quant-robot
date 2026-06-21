# CN Stock Factor Mining Work Report Rounds 1-92 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round92:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current factor candidates ready for backtest: 0
- New factors mined in Round92: 0
- Useful new Round92 capability: real limited-symbol long-history `fina_indicator` backfill smoke passed PIT readiness
- Current next direction: `round93_tushare_fina_indicator_symbol_universe_shard_plan`

The project still has no deployable profitable factor. The useful progress is that the profitability/quality factor path is now backed by real PIT financial input plumbing rather than daily-basic proxies.

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 87 | Public QVM bottom-exclusion walk-forward | two frozen QVM leads accepted 0/7 folds | QVM hibernated |
| 88 | Tushare financial PIT readiness audit | 6,939 existing files scanned, 0 financial-like datasets | profitability mining blocked |
| 89 | `fina_indicator` fixture ingestion smoke | fixture processed 4 rows, 2 assets, 2 quarters; readiness passed | PIT data shape proven |
| 90 | Real Tushare `fina_indicator` smoke | `000001.SZ:20240331` processed 1 real row; readiness passed | real schema path proven |
| 91 | Long-history `fina_indicator` backfill planning | 44 quarters, 88 two-symbol smoke requests, 5 batches; 0 blockers | planner accepted |
| 92 | Limited-symbol long-history `fina_indicator` smoke | 88 requests, 79 deduped processed rows, 9 empty requests, PIT readiness passed | data path accepted; no factor yet |

## Bright Data Worth Remembering

| Area | Bright Data | Final Status |
|---|---|---|
| Low-turnover raw | `turnover_rate_low` +5127.61%, Sharpe 1.983 | rejected as capacity/calendar contaminated |
| Low-turnover raw | `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | rejected as capacity/calendar contaminated |
| Capacity-clean low-turnover | +177.86% / +130.86% clean total return | rejected, overlap Sharpe only 0.410 / 0.294 |
| RSRS | `rsrs_reversal_18_60` +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| RSRS bottom-exclusion diagnostic | overlay t=5.39, positive overlay rate 66.28% | failed costed walk-forward |
| SuperTrend | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Public QVM direct | RankIC 0.0724, t=9.43, capacity-limited trades 0 | rejected, overlap Sharpe 0.226 and max DD -47.71% |
| Public QVM exclusion | mean relative +1.07% / +0.69%, capacity-limited trades 0 | rejected, accepted folds 0/7 |
| Data repair | false +91.71x style return collapsed after adjusted-ratio repair | fake alpha killed correctly |
| Round92 financial data | 2015-2025 limited smoke: 88 requests, 79 deduped rows, duplicate rows 0, PIT-ready datasets 100/100 | accepted data capability, not a factor |

## Why There Is Still No Useful Factor

The validation stack is now correctly hostile to attractive but fragile evidence:

- positive IC did not become robust costed long-only portfolios;
- headline returns often came from illiquidity, stale holding, calendar drift, or implementation artifacts;
- public technical indicators were more useful as loser-avoidance filters than direct buy signals;
- daily-basic valuation proxies were not true profitability data;
- true profitability factors require PIT financial coverage, duplicate control, and announcement-date lag before evaluation.

## Current Conclusion

Round92 improves the data foundation but not the factor scoreboard.

The next useful work is not to pre-register profitability factors yet. It is to build a shard plan for larger `fina_indicator` coverage, then backfill enough PIT financial history to support real quality/profitability hypotheses.
