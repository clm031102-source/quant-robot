# CN Stock Factor Mining Work Report Rounds 1-91 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round91:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current factor candidates ready for backtest: 0
- New factors mined in Round91: 0
- Useful new Round91 capability: long-history `fina_indicator` backfill planner
- Current next direction: `round92_tushare_fina_indicator_limited_symbol_backfill_smoke`

The project still has no deployable profitable factor. The important improvement since Round88 is that the work stopped treating daily-basic valuation proxies as profitability and began building a real PIT financial-data path.

## Rounds 87-91 Completed

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 87 | Public QVM bottom-exclusion walk-forward | two frozen QVM leads both accepted 0/7 folds | QVM hibernated |
| 88 | Tushare financial PIT readiness audit | 6,939 existing files scanned, 0 financial-like datasets | profitability mining blocked |
| 89 | `fina_indicator` fixture ingestion smoke | fixture processed 4 rows, 2 assets, 2 quarters; readiness passed | PIT data shape proven |
| 90 | Real Tushare `fina_indicator` smoke | `000001.SZ:20240331` processed 1 real row; readiness passed | real schema path proven |
| 91 | Long-history `fina_indicator` backfill planning | 44 quarters, 88 smoke requests, 5 batches; 0 blockers | planner accepted; next limited backfill smoke |

## Bright Data Worth Remembering

These were the most visually attractive results across previous rounds. None is currently promotion evidence.

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
| Financial data layer | real `fina_indicator` row has `ann_date`, `end_date`, ROE, margins/growth/cash-flow fields | accepted data capability, not a factor |
| Round91 planner | 2015-2025 = 44 quarters; two-symbol smoke = 88 requests; full current-symbol estimate = 243,276 requests | accepted as next data-governance step |

## Why There Is Still No Useful Factor

The validation stack is now filtering aggressively:

- positive IC did not become a robust costed long-only portfolio;
- headline return often came from illiquidity, stale holding, calendar drift, or implementation artifacts;
- public technical indicators were more useful as loser-avoidance filters than direct buy signals;
- daily-basic proxies were not true profitability data;
- true profitability factors could not be tested until PIT financial data existed;
- large full-universe financial backfill must be planned because the request volume is non-trivial.

## Useful Engineering Outcomes

The project now has reusable infrastructure that is worth keeping:

- long-cycle CN stock authority-data workflow;
- startup gate enforcing CN stock scope, no ETF confusion, and no live-trading boundary crossing;
- three-round review and ten-round GitHub safe-sync governance;
- public indicator families: RSRS, SuperTrend, QVM;
- industry-neutral IC, IC-to-portfolio gap, beta exposure, bottom-exclusion, cost/capacity, and walk-forward diagnostics;
- adjusted-ratio repair and clean authority-bar manifest;
- stock_basic industry metadata foundation;
- Tushare `fina_indicator` mapper, adapter, ingestion path, PIT readiness audit, live smoke, and Round91 backfill planner.

## Current Conclusion

Round91 does not improve the factor scoreboard. It improves the probability that the next factors tested are the right kind of factors.

The correct near-term path is:

1. Run limited-symbol long-history `fina_indicator` backfill smoke.
2. Audit PIT readiness on the processed financial dataset.
3. Only then pre-register profitability/quality factors using `ann_date` as information availability date.
4. Replay any candidate across the 2015-2025 long cycle before promotion discussion.

No factor should be promoted or paper-labeled from the work through Round91.
