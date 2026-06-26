# CN Stock Round292 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round292-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round292 continued the post-review source-construction route. It produced no new factor names, no IC screens, no portfolio grids, and no promotable candidates. This is intentional: the financial reporting timeliness source still has only 349 unique symbols, below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- added 5 net-new point-in-time statement symbols;
- increased aggregate source coverage from 344 to 349 unique symbols;
- preserved the stock-basic pre-listing filter and avoided 24 impossible endpoint requests;
- fixed a combined quality-report bug that could leave stale required-column blockers in the top-level summary;
- confirmed the post-fix standard quality report is internally consistent and passes.

## Startup Gate

Round292 started from the completed Round291 and Round289-291 review state.

| Item | Result |
|---|---|
| Quant PM startup gate | ready |
| Primary project market | CN_ETF remains primary downstream strategy scope |
| This run scope | CN stock factor validation/source construction |
| CN stock startup gate | cleared |
| CN stock data manifest | review_required, no hard blockers |
| Candidate generation | blocked until 1,000 unique symbols |

The manifest warnings remain unchanged: extreme return rows exist in the local bar data, and moneyflow symbol coverage remains below bar coverage. These warnings are not blockers for this source-construction shard, but they still matter before any future factor matrix or portfolio test.

## Pre-Run Overlap Preview

Round292 previewed shard16 offset10 limit5 before spending live endpoint budget.

| Metric | Value |
|---|---:|
| Shard id | 16 |
| Symbol offset | 10 |
| Symbol limit | 5 |
| Financial roots scanned | 97 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |

Net-new symbols:

```text
300589.SZ
002163.SZ
000728.SZ
002697.SZ
000828.SZ
```

Because all five symbols were net-new, the live backfill was allowed.

## Backfill Result

The first live run completed successfully. A second same-parameter rerun was used only to rewrite the reports after the quality-report combine fix; it reused the completed manifest and skipped all 636 endpoint requests.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 220 |
| Active symbol-periods after pre-listing filter | 212 |
| Pre-listing symbol-periods skipped | 8 |
| Endpoint count | 3 |
| Endpoint requests in live segment | 636 |
| Endpoint requests avoided by pre-listing filter | 24 |
| Processed rows | 212 |
| Empty requests | 5 |
| Duplicate rows | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Quality report assets | 5 |
| Quality report rows | 212 |
| Quality report passes | true |

## Quality Report Bug Fixed

Round292 exposed a reporting bug in multi-symbol backfills with pre-listing skips. The per-symbol ingests were combined, but the top-level `summary.blockers` could retain a stale `missing_required_financial_column_group:*` blocker from one child report while `required_column_groups` came from another child report and passed.

Root cause:

- `_combine_quality_reports()` previously unioned child summary blockers;
- it copied the last child report's detailed `required_column_groups`;
- it used the minimum child `required_column_groups_passing`;
- therefore the combined summary and group details could contradict each other.

Fix:

- recompute required-column group pass/fail from all child reports;
- derive group blockers from the recomputed group details;
- keep non-group blockers separately;
- write the combined details and summary from the same facts.

Regression coverage:

- `tests.unit.test_financial_statement_shard_backfill_cli` now includes `test_combined_quality_report_recomputes_group_blockers_from_all_segments`.

Post-fix Round292 quality report:

| Field | Value |
|---|---:|
| rows | 212 |
| assets | 5 |
| duplicate_rows | 0 |
| missing_asset_id_rows | 0 |
| required_column_group_count | 2 |
| required_column_groups_passing | 2 |
| blockers | 0 |
| passes | true |

## Aggregate Source Gate

After Round292, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 98 |
| Aggregate rows | 74,996 |
| Unique symbols | 349 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 344 to 349 unique symbols, but this is still only 34.9% of the 1,000-symbol source gate.

## Factor Outcome

Round292 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is the correct outcome under the current governance. Running financial reporting timeliness IC screens at 349 symbols would repeat the exact short-sample, regime, and multiple-testing failure modes that the new process was designed to stop.

## Decision For Round293

Continue source construction, not candidate generation.

Next allowed direction:

```text
round293_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_overlap_preview_quality_report_recompute_guard_and_empty_response_watch_until_1000_symbols
```

Round293 requirements:

- run startup gates and CN stock data manifest;
- run aggregate-overlap preview before any live endpoint requests;
- scan ahead if preview net-new ratio is below 80%;
- split around existing symbols before live requests;
- keep stock-basic pre-listing filtering mandatory;
- verify the standard quality report summary matches recomputed required-column group details;
- track empty requests and duplicate rows;
- keep candidate generation blocked until the 1,000-symbol source gate clears.
