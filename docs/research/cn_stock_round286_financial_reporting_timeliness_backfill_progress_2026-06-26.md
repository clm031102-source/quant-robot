# CN Stock Round286 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round286-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round286 started from the Round285 closeout state:

- last completed round: 285
- next round: 286
- next direction: `round286_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status: cleared
- CN data manifest: review_required with no hard blockers
- manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage

The source gate still requires at least 1,000 unique symbols before financial reporting timeliness candidate generation. This round therefore performed source construction only.

## Pre-Run Overlap Preview

The live endpoint segment was checked before spending Tushare requests:

| Metric | Value |
|---|---:|
| Shard id | 14 |
| Symbol offset | 15 |
| Symbol limit | 5 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |
| Financial roots scanned | 88 |

Expected net-new symbols:

```text
002679.SZ
002319.SZ
002381.SZ
000791.SZ
000685.SZ
```

Because the preview found 5 / 5 net-new symbols, no scan-ahead was required.

## Backfill Result

Round286 backfilled shard14 offset15 limit5 with the stock-basic pre-listing filter enabled.

| Metric | Value |
|---|---:|
| Selected symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods after pre-listing filter | 220 |
| Endpoint requests executed | 660 |
| Pre-listing skipped symbol-periods | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Processed rows | 220 |
| Empty requests | 0 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Quality report rows | 220 |
| Quality report assets | 5 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |

Selected symbols:

```text
002679.SZ
002319.SZ
002381.SZ
000791.SZ
000685.SZ
```

## Aggregate Source Gate

After the Round286 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 89 |
| Aggregate rows | 69,370 |
| Unique symbols | 322 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 317 to 322 unique symbols, but this is still only 32.2% of the 1,000-symbol source gate.

## Factor Outcome

Round286 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional and correct under the current governance. Running financial reporting timeliness IC screens at 322 symbols would repeat the known short-sample, regime, and multiple-testing failure modes.

## Decision For Round287

Continue source construction only if the next segment passes aggregate-overlap preview. The route remains useful because:

- overlap preview confirmed all five symbols were net-new before live requests;
- true post-filter empty requests stayed at 0;
- required PIT statement fields passed 2 / 2;
- standard quality report rows and assets matched the multi-symbol ingest result.

Next allowed direction:

```text
round287_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
```

Blocked shortcuts:

- no candidate generation before 1,000 unique symbols;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no live backfill without stock-basic pre-listing filter;
- no live backfill without aggregate-overlap preview;
- if preview net-new ratio drops below 80%, scan ahead before spending endpoint budget.
