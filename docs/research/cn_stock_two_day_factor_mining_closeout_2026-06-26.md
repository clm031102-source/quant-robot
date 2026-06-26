# CN Stock Two-Day Factor Mining Closeout

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock cross-sectional alpha research
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

The last two work days moved the project away from blind factor sweeps and toward gated, source-first CN stock alpha research.

The main result is strict but useful:

- promotable factors: 0
- paper-ready factors: 0
- live/manual signals: 0
- families with apparent raw leads that survived hard follow-up gates: 0
- reusable infrastructure and process gates: material improvement
- latest source-construction checkpoint: 331 unique CN stock symbols, still below the 1,000-symbol source gate

This is not a success as alpha production. It is a success as damage control and research-method correction. The process now blocks short-sample profitability claims, ETF/CN-stock scope confusion, raw TopN conversion, and same-family parameter tuning after zero robust leads.

## What Was Built Or Fixed

### Pre-Mining Control Contract

The user-requested control set was turned into mandatory startup and quality gates:

- A-share trading constraints
- point-in-time financial timing
- industry/style neutralization
- ETF versus CN-stock scope separation
- portfolio construction controls
- strict statistics
- China market regime context
- event-factor controls
- final-holdout boundary

The quality gate reported 34 controls, with 33 implemented and 1 not applicable for CN stock. Missing controls, missing evidence, and missing next actions were all zero at the quality-control layer.

This does not make any factor profitable. It means direct factor generation is now blocked unless the correct candidate/source gates are cleared first.

### Tushare Financial Statement Backfill Path

The project now has a reusable path for ordinary financial statement inputs:

- Tushare `income`, `balancesheet`, and `cashflow` endpoint mappings
- combined statement ingest
- readiness and required-column audits
- endpoint-budgeted shard plan
- aggregate source-coverage audit
- startup-gate integration that blocks candidate generation before source coverage is broad enough

The full-universe statement plan covers:

- included symbols: 5,208
- excluded BJ symbols: 321
- periods: 44
- endpoint count per symbol-period: 3
- shards: 261
- estimated total endpoint requests: 687,456

### Forecast And Express Event Cache

Round255 built a reusable forecast/express event cache:

| Feed | Rows | Assets | Event Dates | Date Range | Status |
|---|---:|---:|---:|---|---|
| forecast | 78,573 | 5,728 | 2,681 | 2015-01-01..2025-12-31 | pass |
| express | 20,304 | 4,280 | 1,441 | 2015-01-06..2025-10-22 | pass |

The standalone express surprise factor was rejected, but the cache and PIT loading path are useful reusable infrastructure.

### Startup Governance

The startup config now records:

- last completed round: 288
- next round: 289
- next direction: `round289_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- three-round review cadence
- ten-round packaging cadence
- blocked re-entry families
- required confirmations before the next run

## Research Work Completed

### Event And Public Indicator Families

The work tested or audited Dragon-Tiger, share unlock, pledge relief, public technical indicators, Alpha101-style references, qlib-style references, smart-money references, SuperTrend/OBV/MFI-style composites, listing/board structure, official tradeability events, and industry breadth/regime translation.

The common pattern:

- some raw IC or short-window evidence appeared;
- de-duplication, residualization, year stability, quantile shape, or neutralization removed the apparent edge;
- no family earned portfolio-grid permission.

Most important examples:

- Round248 produced 6 apparent event-context leads, but Round249 reference de-dup and Round250 residual audit reduced them to 0 independent residual leads.
- Round252 replayed 20 public-reference candidates across 60 tests and found 0 research leads.
- Round263 recovered 5 old high-return historical leads with frozen parameters and found 0 recovery candidates.
- Round265 tested 8 public indicator composite candidates and found 0 residual research leads.

### Accounting And Financial Statement Families

Accounting-quality work was expanded, but the first formula families failed:

- raw cash/accrual and asset-growth formulas: 0 leads
- repaired industry-relative accounting formulas: 0 leads
- abnormal accrual change directional clue: not enough after FDR/neutral gates
- post-statement cash-conversion muted reaction: rejected
- realized profitability revision: rejected
- industry-relative statement surprise: underpowered at the existing sample size

The useful conclusion is not "financial statements do not work." It is narrower:

- realized statement formula mutations did not work as standalone alpha in the current sample;
- broader PIT source coverage is required before testing financial reporting timeliness or announcement-delay families responsibly.

### Financial Reporting Timeliness Source Construction

Rounds270-275 changed the work from factor mining to source construction.

Coverage checkpoints:

| Checkpoint | Sources | Aggregate Rows | Unique Symbols | Candidate Plan Allowed |
|---|---:|---:|---:|---|
| Round270 source audit | 3 | 8,926 | 100 max in one source | false |
| after Round272 | 63 | 41,494 | 203 | false |
| after Round273 | 65 | 43,710 | 212 | false |
| after Round274 | 67 | 45,924 | 221 | false |
| after Round275 | 69 | 48,117 | 231 | false |
| after Round276 | 71 | 50,317 | 240 | false |
| after Round277 | 73 | 52,473 | 249 | false |
| after Round278 | 75 | 54,667 | 257 | false |
| after Round279 | 77 | 56,760 | 267 | false |
| after Round280 | 79 | 58,982 | 277 | false |
| after Round281 | 81 | 61,139 | 284 | false |
| after Round282 | 85 | 65,110 | 302 | false |
| after Round283 | 86 | 66,098 | 307 | false |
| after Round284 | 87 | 67,142 | 312 | false |
| after Round285 | 88 | 68,253 | 317 | false |
| after Round286 | 89 | 69,370 | 322 | false |
| after Round287 | 90 | 70,209 | 327 | false |
| after Round288 | 92 | 71,099 | 331 | false |

The source gate requires at least 1,000 unique symbols. The current coverage is 331, or 33.1% of the minimum.

## Round275 Closeout

Round275 completed shard 9 offset 10 and 15:

| Segment | Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---|
| shard9 offset10 limit5 | 5 | 660 | 215 | 23 | 2 | passed |
| shard9 offset15 limit5 | 5 | 660 | 220 | 0 | 0 | passed |
| total | 10 | 1,320 | 435 | 23 | 2 | passed |

Round275 generated no factors, no research leads, no paper-ready candidates, and no promotable factors. That is intentional because the 1,000-symbol source gate did not clear.

New watch item:

- Round275 offset10 had 23 empty endpoint requests and 2 duplicate rows.
- The route remains viable because readiness passed and coverage still increased.
- Round276 must monitor empty-request and duplicate-row rates before more blind continuation.

## Rounds276-288 Closeout

Rounds276-288 continued the same source-construction route instead of prematurely mining factors.

| Round | Segment Work | Incremental Unique Symbols | Processed Rows | Empty Requests | Duplicate Rows | Result |
|---:|---|---:|---:|---:|---:|---|
| 276 | shard10 offset0/5 | +9 | 440 | 0 | 0 | readiness passed |
| 277 | shard10 offset10/15 | +9 | 436 | 17 | 1 | readiness passed |
| 278 | shard11 offset0/5 | +8 | 423 | 53 | 0 | readiness passed; empty spike traced to pre-listing requests |
| 279 | shard11 offset10/15 | +10 | 414 | 0 | 0 | readiness passed; stock-basic pre-listing filter saved 78 endpoint requests |
| 280 | shard12 offset0/5 | +10 | 443 | 0 | 3 | readiness passed; duplicate watch remains active |
| 281 | shard12 offset10/15 | +7 | 430 | 0 | 0 | readiness passed; 3 fetched symbols already existed in older PIT source |
| 282 | shard13 effective non-overlap positions | +18 | 792 | 0 | 0 | readiness passed; 2 already-covered symbols skipped before live requests |
| 283 | shard14 offset0 | +5 | 198 | 0 | 0 | readiness passed; standard quality report now writes combined multi-symbol summary |
| 284 | shard14 offset5 | +5 | 208 | 0 | 0 | readiness passed; pre-listing filter saved 36 endpoint requests |
| 285 | shard14 offset10 | +5 | 220 | 0 | 0 | readiness passed; overlap preview found 5 / 5 net-new symbols |
| 286 | shard14 offset15 | +5 | 220 | 0 | 0 | readiness passed; overlap preview found 5 / 5 net-new symbols |
| 287 | shard15 offset0 | +5 | 167 | 0 | 0 | readiness passed; pre-listing filter saved 159 endpoint requests |
| 288 | shard15 offset5/7 net-new subsegments | +4 | 176 | 0 | 0 | readiness passed; overlap preview skipped 1 already-covered symbol |

Useful engineering output from these thirteen rounds:

- shard 10 completed;
- shard 11 completed;
- shard 12 completed;
- shard 13 effective non-overlap positions completed;
- shard 14 completed;
- aggregate source coverage increased from 231 to 331 unique symbols;
- the Round278 empty-request cluster was diagnosed as pre-listing request waste;
- the backfill CLI now supports a mandatory stock-basic pre-listing filter;
- the Round279 combined quality-report bug was fixed and regression-tested;
- Round280 proved the filter must remain mandatory even when a segment has zero pre-listing skips;
- Round281 exposed a new efficiency requirement: preview aggregate symbol overlap before live endpoint requests;
- a reusable overlap preview script now checks expected net-new symbols before spending live endpoint budget.
- Round282 used that preview to skip `000514.SZ` and `000151.SZ` before live endpoint requests, saving roughly 264 endpoint requests versus blind contiguous blocks.
- Round283 found and fixed a second quality-report issue: when pre-listing filters force per-symbol ingests, the standard `financial_statement_quality_report.json` is now overwritten with the combined multi-symbol summary instead of the final symbol's summary.
- Round284 completed the required 282-284 three-round review and tightened the next-run rule: scan ahead if preview net-new ratio drops materially below 80%.
- Round285 confirmed the overlap-preview rule is efficient on shard14 offset10: all five names were net-new, 660 endpoint requests produced 220 rows, and post-filter empty requests stayed at 0.
- Round286 continued the same efficient path on shard14 offset15: all five names were net-new, 660 endpoint requests produced 220 rows, and post-filter empty requests stayed at 0.
- Round287 started shard15 with 5 / 5 net-new symbols, used the pre-listing filter to avoid 159 endpoint requests, and kept post-filter empty requests at 0.
- Round288 extended the preview rule from "continue or scan ahead" to "split around known overlaps": it skipped `000088.SZ`, backfilled only four net-new names, and avoided duplicate live endpoint spend.

Factor outcome across Rounds276-288:

- new factor names: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is the correct outcome under the current gate. The source is still below 1,000 unique symbols, so portfolio grids or IC screens would be short-sample overfitting, not valid alpha research.

## What Is Actually Useful

The useful output is not a profitable signal yet. The useful output is:

1. A clean CN-stock mandate separated from CN ETF rotation.
2. A startup gate that prevents repeating known bad families.
3. A quality gate that encodes the user's eight required control areas.
4. A candidate-plan policy that requires hypothesis source and promotion policy before factor generation.
5. A long-cycle 2015-2025 replay standard.
6. A final-holdout boundary that blocks 2026 tuning.
7. A reusable Tushare forecast/express event cache.
8. A reusable ordinary financial-statement backfill path.
9. An aggregate financial reporting timeliness source audit.
10. A hard decision not to promote raw high-return or high-IC results without residual, walk-forward, cost/capacity, regime, and strict-statistics evidence.

## Why There Are No Good Factors Yet

The factor results are poor for structural reasons:

- many apparent signals are style, industry, liquidity, size, or tradeability exposures;
- several raw leads are redundant with their own component legs or public references;
- some event datasets are sparse or unstable by year;
- several financial statement formulas are underpowered because PIT statement coverage is still small;
- some old high-return rows fail overlap, drawdown, extreme-trade, capacity, or walk-forward gates;
- the new workflow intentionally blocks short-window overfitting instead of converting weak evidence into portfolio tests.

## Direction Decision

Do not return to blind moneyflow, raw public-indicator, or same-family parameter sweeps.

The next allowed work is Round289:

```text
financial reporting timeliness backfill with stock-basic pre-listing filter and aggregate-overlap preview
```

Round289 must do one of two things:

1. Continue financial reporting timeliness backfill with the stock-basic pre-listing filter and a pre-run aggregate-overlap preview.
2. Rotate only if the backfill route stops increasing coverage, becomes too costly, or fails required PIT field readiness.

Blocked shortcuts:

- no candidate generation before 1,000-symbol source coverage;
- no short-sample IC screen;
- no portfolio grid;
- no paper-ready or live-signal claim;
- no final-holdout access;
- no ignoring aggregate symbol overlap after Round281.
- no trusting a per-symbol quality report after a multi-symbol ingest; the standard quality file must match the combined ingest summary.

## Verification

Latest closeout verification:

- JSON validation passed for `configs/factor_mining_startup_cn_stock.json`.
- 62 relevant unit tests passed.
- Project audit passed with 1,795 files scanned and 0 factor registry unknowns.
- `git diff --check` passed.
- exact Tushare token scan passed for committed configs, docs, and tests.
- Round289 startup gate should clear with Round288 completed and Round289 next before the next live endpoint spend.
- staged path audit confirmed no `data/` or `logs/` paths were committed.
