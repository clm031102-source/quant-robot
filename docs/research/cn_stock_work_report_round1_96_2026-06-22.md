# CN Stock Factor Mining Work Report Rounds 1-96 - 2026-06-22

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round96:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round96 pre-registered profitability-quality candidates: 14
- Round96 candidates coverage-passed for next smoke: 14
- Current next direction: `round97_profitability_quality_factor_matrix_smoke_and_label_alignment`

Round96 is the first round in this corrected profitability-quality path that produced actual named factor candidates. They are useful research candidates, not tradable factors.

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
| 95 | Shard 1 full100 live backfill | 4,400 requests, 4,328 processed rows, 72 empty requests, duplicate rows 0, PIT readiness passed | full shard accepted; preregistration next |
| 96 | Profitability-quality preregistration | 14 candidates, 14 coverage-passed, 0 data/PIT blockers | candidates accepted for matrix smoke |

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
| SuperTrend | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Public QVM direct | RankIC 0.0724, t=9.43, capacity-limited trades 0 | rejected, overlap Sharpe 0.226 and max DD -47.71% |
| Data repair | false +91.71x style return collapsed after adjusted-ratio repair | fake alpha killed correctly |
| Round95 financial data | 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT-ready datasets 4,412/4,412 | accepted data capability |
| Round96 preregistration | 14/14 candidates coverage-passed; lowest row coverage 90.73% | accepted candidate capability |

## Current Conclusion

The project still has no deployable profitable factor. The corrected path is now productive enough to continue: the 14 profitability-quality candidates are named, economically interpretable, PIT-aware, and covered well enough on the 100-symbol shard to enter a factor-matrix and label-alignment smoke.

Next step:

```text
round97_profitability_quality_factor_matrix_smoke_and_label_alignment
```
