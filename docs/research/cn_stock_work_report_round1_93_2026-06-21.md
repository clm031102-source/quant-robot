# CN Stock Factor Mining Work Report Rounds 1-93 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round93:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current factor candidates ready for backtest: 0
- New factors mined in Round93: 0
- Useful new Round93 capability: deterministic broad-universe `fina_indicator` shard plan for true profitability-quality data
- Current next direction: `round94_tushare_fina_indicator_first10_symbol_shard_backfill_smoke`

The project still has no deployable profitable factor. The important progress is that the process has stopped treating attractive short-window or proxy evidence as usable alpha and is now building the missing PIT financial data layer needed for real profitability and quality factors.

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 87 | Public QVM bottom-exclusion walk-forward | two frozen QVM leads accepted 0/7 folds | QVM hibernated |
| 88 | Tushare financial PIT readiness audit | 6,939 existing files scanned, 0 financial-like datasets | profitability mining blocked |
| 89 | `fina_indicator` fixture ingestion smoke | fixture processed 4 rows, 2 assets, 2 quarters; readiness passed | PIT shape proven |
| 90 | Real Tushare `fina_indicator` smoke | `000001.SZ:20240331` processed 1 real row; readiness passed | real schema path proven |
| 91 | Long-history `fina_indicator` backfill planning | 44 quarters, 88 two-symbol smoke requests, 5 batches; 0 blockers | planner accepted |
| 92 | Limited-symbol long-history `fina_indicator` smoke | 88 requests, 79 deduped processed rows, 9 empty requests, PIT readiness passed | data path accepted; no factor |
| 93 | Broad-universe `fina_indicator` shard plan | 5,208 included symbols, 44 quarters, 229,152 planned requests, 53 shards | first-10-symbol shard smoke required before expansion |

## Bright Data Worth Remembering

These numbers are useful, but none is promotion evidence by itself.

| Area | Bright Data | Final Status |
|---|---|---|
| ETF range contraction lead | `formula_range_contraction_breakout_20_top5_cost5_reb10` Sharpe about 1.83, annual return about 1.9%, max DD about -0.24% | research lead only; adjusted IC p=1.0 and cost fragility blocked promotion |
| Low-turnover raw | `turnover_rate_low` +5127.61%, Sharpe 1.983 | rejected as capacity/calendar contaminated |
| Low-turnover raw | `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | rejected as capacity/calendar contaminated |
| Capacity-clean low-turnover | +177.86% / +130.86% clean total return | rejected, overlap Sharpe only 0.410 / 0.294 |
| Public price-volume formulas | `formula_pv_corr_reversal_20` RankIC about 0.076, t=10.88 | portfolio translation failed |
| Industry-neutral public formulas | neutral RankIC about 0.088-0.091, t near 49 | strong IC, weak portfolio Sharpe |
| Bottom-exclusion overlays | overlay t up to 8.46, positive rate about 70% | costed portfolios failed drawdown/Sharpe gates |
| Daily-basic residuals | neutral RankIC 0.042-0.056 | long-only conversion failed |
| Benchmark beta diagnostics | residual alpha t=4.39-5.42 | beta dominance too high |
| RSRS | `rsrs_reversal_18_60` +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| RSRS bottom-exclusion diagnostic | overlay t=5.39, positive overlay rate 66.28% | failed costed walk-forward |
| SuperTrend | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Public QVM direct | RankIC 0.0724, t=9.43, capacity-limited trades 0 | rejected, overlap Sharpe 0.226 and max DD -47.71% |
| Public QVM exclusion | mean relative +1.07% / +0.69%, capacity-limited trades 0 | rejected, accepted folds 0/7 |
| Data repair | false +91.71x style return collapsed after adjusted-ratio repair | fake alpha killed correctly |
| Round92 financial data | 2015-2025 limited smoke: 88 requests, 79 deduped rows, duplicate rows 0, PIT-ready datasets 100/100 | accepted data capability, not a factor |
| Round93 financial shard plan | 5,208 non-BJ symbols, 44 quarters, 229,152 requests, 53 shards | accepted cost-control plan, not a factor |

## What Was Built Or Hardened

Reusable research infrastructure now includes:

- startup gate for CN stock factor-mining context;
- three-round review cadence and ten-round GitHub safe-sync cadence;
- long-cycle 2015-2025 replay discipline;
- same-parameter full-sample diagnostics;
- rolling walk-forward train/test validation;
- cost, market-impact, capacity, and signal-date liquidity gates;
- calendar holding drift detection;
- overlap-adjusted return statistics;
- multiple-testing and source-evidence gates;
- industry-neutral IC and IC-to-portfolio gap diagnostics;
- benchmark beta exposure and beta-hedged spread audit;
- bottom-exclusion translation-layer testing;
- public RSRS, SuperTrend, and QVM factor families;
- Tushare daily-basic alpha factory;
- Tushare `fina_indicator` ingestion, manifest, quality report, and PIT readiness path;
- resume-safe long-history financial backfill planning;
- limited-symbol live financial backfill smoke;
- broad-universe financial shard planning.

## Why There Is Still No Useful Factor

The validation stack is now correctly hostile to attractive but fragile evidence:

- positive IC did not become robust costed long-only portfolios;
- high full-sample returns often came from illiquidity, sparse trading, calendar drift, or data artifacts;
- public technical indicators were more useful as loser-avoidance filters than direct buy signals;
- daily-basic valuation and liquidity proxies were not true profitability data;
- true profitability factors require PIT financial coverage, duplicate control, and announcement-date lag before evaluation;
- no candidate has survived long-cycle replay, cost/capacity controls, overlap-aware statistics, drawdown, benchmark-relative behavior, walk-forward accepted folds, and multiple-testing discipline together.

## Current Conclusion

Round93 improves the data foundation but not the factor scoreboard.

The correct next step is still not to mine or promote profitability factors directly. Round94 should run the first 10 symbols from shard 1 across the full 2015-2025 quarterly period:

```text
10 symbols * 44 quarters = 440 requests
```

Only if that smoke passes runtime, duplicate-row, PIT readiness, and empty-response quality gates should the project move to a full 100-symbol shard. Profitability-quality factors should be pre-registered only after enough PIT financial history exists to avoid look-ahead bias and proxy substitution.
