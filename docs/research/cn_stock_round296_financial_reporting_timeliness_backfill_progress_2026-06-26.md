# CN Stock Round296 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round296-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round296 continued the source-first route and produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 366 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- ran the Quant PM and CN stock startup gates before endpoint spend;
- previewed shard17 offset9 limit5 before live requests;
- confirmed all five selected symbols were net-new;
- backfilled 5 net-new PIT statement symbols;
- increased aggregate source coverage from 361 to 366 unique symbols;
- recovered cleanly from a live API timeout by rerunning the same output directory with `resume=True`;
- kept duplicate rows at 0 and required financial column groups at 2 / 2;
- recorded 2 empty endpoint responses for monitoring before factor matrix construction.

## Startup Gate

Round296 started from the completed Round295 state.

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

Round296 previewed shard17 offset9 limit5.

| Metric | Value |
|---|---:|
| Shard id | 17 |
| Symbol offset | 9 |
| Symbol limit | 5 |
| Financial roots scanned | 101 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |

Preview symbols:

```text
000529.SZ
002100.SZ
002155.SZ
000997.SZ
600696.SH
```

Because all five symbols were net-new, the live batch stayed at shard17 offset9 limit5.

## Backfill Result

Round296 backfilled the five net-new symbols with stock-basic pre-listing filtering enabled.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 220 |
| Active symbol-periods | 220 |
| Pre-listing symbol-periods skipped | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Endpoint count | 3 |
| Endpoint requests | 660 |
| Processed rows | 220 |
| Empty requests | 2 |
| Duplicate rows | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Quality report assets | 5 |
| Quality report rows | 220 |
| Quality report passes | true |

Net-new symbols:

```text
000529.SZ
002100.SZ
002155.SZ
000997.SZ
600696.SH
```

Quality date coverage:

| Field | Range |
|---|---|
| Announcement date | 2015-04-25 to 2026-04-30 |
| Report period | 2015-03-31 to 2025-12-31 |

## Timeout Recovery Note

The first live backfill attempt timed out at the shell command boundary after raw parquet files had been written but before the final quality and shard reports were emitted. Investigation showed:

- the output directory contained raw parquet files only;
- no final `financial_statement_quality_report.json` or shard report existed yet;
- the backfill script calls the Tushare financial statement ingest with `resume=True`.

The same command was rerun with the same output directory and a longer command timeout. It reused the existing raw files and completed the quality report and processed statement inputs. This is an external API latency/command-timeout issue, not a failed source batch.

## Aggregate Source Gate

After Round296, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 102 |
| Aggregate rows | 78,623 |
| Unique symbols | 366 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 361 to 366 unique symbols. This is 36.6% of the 1,000-symbol source gate.

## Factor Outcome

Round296 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is the correct outcome. Testing financial reporting timeliness at 366 symbols would still be underpowered and vulnerable to false positives.

## Decision For Round297

Continue source construction, not candidate generation.

Next allowed direction:

```text
round297_continue_financial_reporting_timeliness_backfill_on_shard17_offset14_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```

Round297 requirements:

- preview shard17 offset14 before any live request;
- scan ahead if preview net-new ratio is below 80%;
- split around existing symbols before live requests;
- keep stock-basic pre-listing filtering mandatory;
- verify standard quality report summaries against recomputed required-column groups;
- track empty requests and duplicate rows;
- keep candidate generation blocked until the 1,000-symbol source gate clears.
