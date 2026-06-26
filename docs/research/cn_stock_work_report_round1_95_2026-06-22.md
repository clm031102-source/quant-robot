# CN Stock Factor Mining Work Report Rounds 1-95 - 2026-06-22

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round95:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current factor candidates ready for backtest: 0
- New factors mined in Round95: 0
- Useful new Round95 capability: 100-symbol, 2015-2025, point-in-time Tushare `fina_indicator` shard backfill with duplicate and PIT gates passing
- Current next direction: `round96_profitability_quality_factor_preregistration_and_coverage_audit`

The project still has no deployable profitable factor. The valuable progress is that the work has stopped forcing weak moneyflow/public-technical families and is now rebuilding the CN-stock profitability-quality path from audited Tushare financial data.

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 88 | Tushare financial PIT readiness audit | 6,939 existing files scanned, 0 financial-like datasets | profitability mining blocked |
| 89 | `fina_indicator` fixture ingestion smoke | fixture processed 4 rows, 2 assets, 2 quarters; readiness passed | PIT shape proven |
| 90 | Real Tushare `fina_indicator` smoke | `000001.SZ:20240331` processed 1 real row; readiness passed | real schema path proven |
| 91 | Long-history `fina_indicator` backfill planning | 44 quarters, 88 two-symbol smoke requests, 5 batches; 0 blockers | planner accepted |
| 92 | Limited-symbol long-history `fina_indicator` smoke | 88 requests, 79 deduped processed rows, 9 empty requests, PIT readiness passed | data path accepted; no factor |
| 93 | Broad-universe `fina_indicator` shard plan | 5,208 included symbols, 44 quarters, 229,152 planned requests, 53 shards | first10 smoke required |
| 94 | Shard 1 first10 live smoke | 440 requests, 429 processed rows, 11 empty requests, duplicate rows 0, PIT readiness passed | first10 accepted; full shard next |
| 95 | Shard 1 full100 live backfill | 4,400 requests, 4,328 processed rows, 72 empty requests, duplicate rows 0, PIT readiness passed | full shard accepted; pre-register profitability-quality candidates next |

## Bright Data Worth Remembering

| Area | Bright Data | Final Status |
|---|---|---|
| ETF range contraction lead | Sharpe about 1.83, annual return about 1.9%, max DD about -0.24% | research lead only; adjusted IC p=1.0 and cost fragility blocked promotion |
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
| Round94 financial data | 10-symbol first shard smoke: 440 requests, 429 processed rows, duplicate rows 0, PIT-ready datasets 452/452 | accepted data capability, not a factor |
| Round95 financial data | 100-symbol shard: 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT-ready datasets 4,412/4,412 | accepted data capability, not a factor |

## Why the Results Still Look Poor

The earlier factor families found attractive-looking pieces of evidence, but none survived the promotion path:

- strong IC often failed to convert into costed long-only portfolio returns;
- raw high-return low-turnover lines were contaminated by capacity and calendar-holding issues;
- public indicators such as RSRS, SuperTrend, and QVM had research leads but failed walk-forward or costed portfolio gates;
- regime and bottom-exclusion overlays improved relative diagnostics but did not fix absolute drawdown and Sharpe;
- the project did not have PIT financial statement data ready, so true profitability-quality factors could not be honestly tested.

That is why the correct current move is not more parameter sweeping. It is to build audited financial inputs, pre-register economically meaningful profitability candidates, and only then run long-cycle validation.

## Current Conclusion

Round95 materially improves the future profitability-quality path, but it still does not justify mining or promoting factors.

The next useful step is:

```text
round96_profitability_quality_factor_preregistration_and_coverage_audit
```

Round96 should generate candidate definitions and coverage thresholds from the clean shard data, then decide whether to expand the financial backfill further or run the first long-cycle profitability-quality factor screens.
