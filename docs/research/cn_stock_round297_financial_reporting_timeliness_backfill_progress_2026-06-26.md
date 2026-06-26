# CN Stock Round297 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round297-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round297 continued the source-first route and produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 371 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- ran the Quant PM and CN stock startup gates before endpoint spend;
- previewed shard17 offset14 limit5 before live requests;
- confirmed all five selected symbols were net-new;
- backfilled 5 net-new PIT statement symbols;
- increased aggregate source coverage from 366 to 371 unique symbols;
- kept duplicate rows at 0 and required financial column groups at 2 / 2;
- recorded 5 empty endpoint responses for monitoring before factor matrix construction.

## Startup Gate

Round297 started from the completed Round296 state.

| Item | Result |
|---|---|
| Quant PM startup gate | ready |
| Primary project market | CN_ETF remains primary downstream strategy scope |
| This run scope | CN stock factor validation/source construction |
| CN stock startup gate | cleared |
| CN stock data manifest | review_required, no hard blockers |
| Candidate generation | blocked until 1,000 unique symbols |

The manifest warnings remain:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

These do not block this statement-source backfill, but they still need explicit handling before future factor promotion.

## Pre-Run Overlap Preview

Round297 previewed shard17 offset14 limit5.

| Metric | Value |
|---|---:|
| Shard id | 17 |
| Symbol offset | 14 |
| Symbol limit | 5 |
| Financial roots scanned | 102 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |

Preview symbols:

```text
000880.SZ
000623.SZ
002719.SZ
002115.SZ
002120.SZ
```

Because all five symbols were net-new, the live batch stayed at shard17 offset14 limit5.

## Backfill Result

Round297 backfilled the five net-new symbols with stock-basic pre-listing filtering enabled.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 220 |
| Active symbol-periods | 220 |
| Pre-listing symbol-periods skipped | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Endpoint count | 3 |
| Endpoint requests | 660 |
| Processed rows | 220 |
| Empty requests | 5 |
| Duplicate rows | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Quality report assets | 5 |
| Quality report rows | 220 |
| Quality report passes | true |

Net-new symbols:

```text
000880.SZ
000623.SZ
002719.SZ
002115.SZ
002120.SZ
```

Quality date coverage:

| Field | Range |
|---|---|
| Announcement date | 2015-04-21 to 2026-04-28 |
| Report period | 2015-03-31 to 2025-12-31 |

## Aggregate Source Gate

After Round297, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 103 |
| Aggregate rows | 79,726 |
| Unique symbols | 371 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 366 to 371 unique symbols. This is 37.1% of the 1,000-symbol source gate.

## Factor Outcome

Round297 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is the correct outcome. Testing financial reporting timeliness at 371 symbols would still be underpowered and vulnerable to false positives.

## Decision For Round298

Continue source construction, not candidate generation.

Next allowed direction:

```text
round298_continue_financial_reporting_timeliness_backfill_on_shard17_offset19_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_then_round296_298_review
```

Round298 requirements:

- preview shard17 offset19 before any live request;
- scan ahead if preview net-new ratio is below 80%;
- split around existing symbols before live requests;
- keep stock-basic pre-listing filtering mandatory;
- verify standard quality report summaries against recomputed required-column groups;
- track empty requests and duplicate rows;
- keep candidate generation blocked until the 1,000-symbol source gate clears;
- after Round298 completes, run the required Round296-298 three-round review before further endpoint spend.
