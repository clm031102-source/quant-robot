# Office Desktop Two-Day Full Closeout Through Round298

- Date: 2026-06-26
- Machine: office_desktop
- Task: factor_validation
- Scope: CN A-share stock factor research support and financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

The two-day work block produced 0 promotable factors, 0 paper-ready candidates, and 0 live/manual trading signals.

That is the correct research outcome under the stricter gates now in the project. The office desktop stopped blind factor expansion and moved into a source-first role: build a point-in-time, long-cycle, broad-enough financial statement source before allowing financial reporting timeliness factors to be mined.

The useful output is not an alpha claim. The useful output is a better research machine:

- CN stock scope is separated from the downstream CN ETF rotation problem.
- Startup gates now force scope, branch, push, source, long-cycle, holdout, and promotion-policy checks.
- Failed families are hibernated unless a new orthogonal source or hypothesis appears.
- Public-indicator and historical high-return artifacts are blocked from promotion without residual, capacity, and walk-forward evidence.
- Financial reporting timeliness source construction now uses overlap preview, split-around-existing-symbols, pre-listing filters, quality-report recomputation, and a memory-safe aggregate source audit.

## Current Quantitative Status

| Area | Result |
|---|---:|
| Promotable/live factors | 0 |
| Paper-ready factors | 0 |
| New usable live/manual signals | 0 |
| New factors generated in Rounds292-298 | 0 |
| IC screens in Rounds292-298 | 0 |
| Portfolio grids in Rounds292-298 | 0 |
| Financial reporting timeliness aggregate sources | 104 |
| Financial reporting timeliness aggregate rows | 79,950 |
| Financial reporting timeliness unique symbols | 372 / 1,000 |
| Source-ready roots for this family | 0 |
| Candidate generation allowed for this family | false |
| CN bar rows in local manifest | 15,930,072 |
| CN bar symbols in local manifest | 5,774 |
| CN moneyflow rows in local manifest | 14,702,368 |
| CN moneyflow symbols in local manifest | 5,648 |

Round270's aggregate source audit had about 100 usable unique symbols. Round298 reached 372. That is roughly +272 unique symbols, but still only 37.2% of the 1,000-symbol minimum gate.

## Two-Day Direction Correction

The major conceptual correction was scope separation:

- The office desktop is currently responsible for CN A-share stock factor validation and source construction.
- The project's primary downstream strategy remains CN ETF rotation.
- CN stock factors are not automatically ETF rotation factors; they need a later translation layer into ETF-level allocation, industry breadth, sector risk, macro/regime state, or constituent-weighted signals.

This prevents three specific mistakes:

- treating CN stock TopN backtests as ETF allocation evidence;
- treating Tushare individual-stock data spend as automatically useful for ETF rotation;
- chasing one factor family, such as moneyflow, after hard gates show that it is not producing robust alpha.

## What Was Built Or Fixed

### Governance And Startup Gates

The project now requires each serious run to confirm:

- machine, task type, branch, and push policy;
- CN stock scope versus ETF downstream scope;
- candidate plan and source readiness;
- 2015-2025 long-cycle replay before promotion;
- walk-forward and out-of-sample separation;
- lookahead, overfit, multiple-testing, and overlap-aware statistics;
- cost, capacity, turnover, regime, industry, and style controls;
- final-holdout protection.

Cadence is explicit:

- every 3 rounds: review and audit the last block before continuing;
- every 10 rounds: package and sync;
- after a failed family: rotate unless a genuinely new orthogonal source or hypothesis exists.

### Failed Or Blocked Research Families

The following directions were tested, audited, or explicitly hibernated:

- moneyflow and smart-money variants;
- low-turnover and daily-basic portfolio grids;
- public technical indicators including OBV, MFI, SuperTrend, MACD, and RSI composites;
- Alpha101/Alpha158-style public price-volume references;
- Dragon-Tiger, share unlock, pledge relief, index rebalance, forecast, and express-event paths;
- accounting-quality formula mutations before broad enough PIT statement coverage.

Useful negative result: these routes should not receive more parameter sweeps unless a new source, economic mechanism, or orthogonalization proof appears.

### PIT Financial Statement Source Pipeline

The strongest constructive output is the financial statement source pipeline:

- Tushare `income`, `balancesheet`, and `cashflow` ingestion;
- endpoint-budgeted statement shard plan;
- point-in-time readiness audit;
- required financial column group checks;
- stock-basic listing-date pre-filter;
- aggregate-overlap preview before live endpoint spend;
- split-around-overlap workflow;
- source gate that blocks factor generation before 1,000 unique symbols.

### Quality And Source-Audit Reliability

Three reliability issues were fixed or guarded:

- combined multi-symbol reports now write the standard `financial_statement_quality_report.json`;
- combined required-column group blockers are recomputed from all child segments instead of keeping stale child blockers;
- the source audit now reads only minimal timeliness columns and expands broad `data/processed` roots into financial child roots, preventing accidental non-financial parquet loads.

This matters because a stale quality report or broad-root memory failure can either block valid progress or let an invalid source into factor mining.

## Recent Round Progress

| Round Block | Work | Net-New Symbols | Processed Rows | Empty Requests | Duplicate Rows | Aggregate Symbols |
|---|---|---:|---:|---:|---:|---:|
| Round270 source audit | source gate audit | baseline | 8,926 | n/a | n/a | 100 |
| Rounds276-288 | shard10-15 source backfill and process fixes | +100 from Round275 state | 4,485 | 70 | 4 | 331 |
| Rounds289-291 | three-round block | +13 | 576 | 40 | 4 | 344 |
| Rounds292-295 | source block | +17 | 707 | 5 | 0 | 361 |
| Rounds296-298 | latest reviewed source block | +11 | 484 | 7 | 0 | 372 |

Latest round detail:

| Round | Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Pre-Listing Requests Avoided | Aggregate Symbols |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 292 | shard16 offset10 limit5 | 5 | 636 | 212 | 5 | 0 | 24 | 349 |
| 293 | shard16 offset16 limit4 | 4 | 528 | 176 | 0 | 0 | 0 | 353 |
| 294 | shard17 offset0 limit4 | 4 | 447 | 149 | 0 | 0 | 81 | 357 |
| 295 | shard17 offset5 limit4 | 4 | 510 | 170 | 0 | 0 | 18 | 361 |
| 296 | shard17 offset9 limit5 | 5 | 660 | 220 | 2 | 0 | 0 | 366 |
| 297 | shard17 offset14 limit5 | 5 | 660 | 220 | 5 | 0 | 0 | 371 |
| 298 | shard17 offset19 limit5 | 1 | 132 | 44 | 0 | 0 | 0 | 372 |
| Total | Rounds292-298 | 28 | 3,573 | 1,191 | 12 | 0 | 123 | 372 |

Round296-298 net-new symbols:

```text
000529.SZ
002100.SZ
002155.SZ
000997.SZ
600696.SH
000880.SZ
000623.SZ
002719.SZ
002115.SZ
002120.SZ
000669.SZ
```

## What Is Actually Useful

Useful content produced in this block:

- A repeatable startup gate that prevents ETF/CN-stock scope confusion.
- A source gate that blocks financial reporting timeliness mining before 1,000 unique symbols.
- A stock-basic pre-listing filter that avoids impossible Tushare statement requests.
- An aggregate-overlap preview that prevents spending endpoint budget on already-covered symbols.
- A split-around-overlap rule for shard work.
- Regression-tested quality-report recompute and standard-summary fixes.
- A memory-safe aggregate source audit that ignores unrelated non-financial parquet files.
- A long-cycle same-parameter walk-forward promotion policy.
- A documented hibernation list for repeatedly failed factor families.
- A current source baseline of 104 roots, 79,950 rows, and 372 unique symbols.

## Why There Are Still No Useful Factors

No candidate has survived the gates that matter. The main failure modes were:

- short-sample or single-regime exposure;
- parameter sweep overfitting;
- raw IC disappearing after industry/style neutralization;
- headline return depending on extreme trades;
- capacity or turnover cost fragility;
- redundancy with component legs or public references;
- insufficient PIT source coverage;
- no stable walk-forward out-of-sample behavior.

For financial reporting timeliness specifically, the idea is not rejected. The source is not broad enough yet. Testing at 372 symbols would invite false positives, so IC screens, portfolio grids, paper-ready labels, and live/manual signals remain blocked.

## Remaining Gaps

- Financial reporting timeliness coverage is still 372 / 1,000.
- Source construction is endpoint-expensive.
- CN stock factors still need a disciplined translation path into CN ETF rotation.
- The project still has many historical experiment rows but few reusable positive insights.
- Future candidate generation should start from public/economic hypotheses and strict source gates, not blind parameter expansion.

## Decision And Next Direction

Do not promote any factor from this two-day block.

Continue source construction only:

```text
round299_start_with_round296_298_three_round_review_then_continue_financial_reporting_timeliness_backfill_on_shard18_offset0_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```

Round299 requirements:

- read the Round296-298 review before live endpoint spend;
- preview shard18 offset0 before live requests;
- scan ahead if the net-new ratio is below 80%;
- split around existing symbols before live requests;
- keep stock-basic pre-listing filtering mandatory;
- recompute and verify required-column group quality summaries;
- track empty requests and duplicate rows;
- keep candidate generation blocked until the 1,000-symbol source gate clears.
