# CN Stock Tushare Fina Indicator Shard1 Full100 Backfill Round95 - 2026-06-22

## Executive Summary

Round95 produced no new factor and no profitability claim. It expanded the real Tushare `fina_indicator` backfill from the Round94 first10 smoke to the full first shard of 100 CN A-share stock symbols across 44 quarterly periods from 2015-03-31 through 2025-12-31.

The important result is that the profitability-quality data path is now clean at a 100-symbol shard scale: all 4,400 raw request partitions were written, processed rows were non-zero, duplicate financial keys were 0, missing asset ids were 0, and PIT readiness passed.

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks, not ETF rotation
- Source shard plan: `data/reports/fina_indicator_symbol_shard_plan_round93_20260621/fina_indicator_symbol_shard_plan.json`
- Shard: 1
- Selected symbols: 100
- Periods: 44 quarterly periods from `20150331` through `20251231`
- Safety: research-to-review only; no broker, account, order, or live-trading action

Selected symbol range:

```text
000001.SZ ... 000516.SZ
```

## Command

```powershell
python scripts\run_fina_indicator_shard_backfill_smoke.py --shard-plan-json data\reports\fina_indicator_symbol_shard_plan_round93_20260621\fina_indicator_symbol_shard_plan.json --shard-id 1 --max-symbols 100 --batch-size 20 --max-requests 4400 --output-dir data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --pit-readiness-output-dir data\reports\tushare_financial_pit_readiness_round95_shard1_full100_20260622
```

## Live Backfill Result

| Metric | Value |
|---|---:|
| Selected symbols | 100 |
| Periods | 44 |
| Planned requests | 4,400 |
| Downloaded raw partitions | 4,400 |
| Runtime | about 1h28m43s |
| Processed rows | 4,328 |
| Empty requests | 72 |
| Empty request rate | 1.64% |
| Skipped requests | 0 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |
| Assets | 100 |
| Ann date range | 2015-04-15 to 2026-04-30 |
| Report period range | 2015-03-31 to 2025-12-31 |

Missing numeric fields:

| Field | Missing Rows |
|---|---:|
| `grossprofit_margin` | 88 |
| `roa` | 87 |
| `roe` | 39 |
| `netprofit_margin` | 1 |
| Any tracked numeric field | 215 |

## PIT Readiness

| Metric | Value |
|---|---:|
| Passes | true |
| Blockers | 0 |
| Files scanned | 4,415 |
| Financial-like datasets | 4,412 |
| PIT-ready datasets | 4,412 |

## Research Decision

Round95 is accepted as data-pipeline progress, not factor progress.

Current factor status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round95 factor candidates: 0

This shard is large enough to start pre-registering profitability-quality hypotheses and coverage gates, but it is not large enough to promote factors or claim profitability.

## Next Direction

Round96 should pre-register profitability-quality candidates and run a coverage audit before any backtest:

```text
round96_profitability_quality_factor_preregistration_and_coverage_audit
```

Candidate families may include:

- profitability level: ROE, ROA, net profit margin, gross margin;
- profitability change: ROE/ROA/margin year-over-year or rolling change;
- profit growth quality: net profit growth versus operating revenue growth;
- cash-profit quality: operating cash-flow per share versus earnings/profitability;
- stability: multi-quarter persistence, volatility, and drawdown of profitability metrics.

Required gates before any factor backtest:

- field coverage threshold by date and symbol;
- announcement-date information availability;
- no use of report-period data before `ann_date`;
- no direct promotion from a single shard;
- long-cycle same-parameter replay after a candidate is registered.
