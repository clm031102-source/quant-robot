# CN Stock Round284 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round284-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round284 started from the Round283 closeout state:

- last completed round: 283
- next round: 284
- next direction: `round284_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status: cleared
- CN data manifest: review_required with no hard blockers
- manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage

The source gate still requires at least 1,000 unique symbols before financial reporting timeliness candidate generation. This round therefore performed source construction only.

## Pre-Run Overlap Preview

The live endpoint segment was checked before spending Tushare requests:

| Metric | Value |
|---|---:|
| Shard id | 14 |
| Symbol offset | 5 |
| Symbol limit | 5 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |
| Financial roots scanned | 86 |

Expected net-new symbols:

```text
002103.SZ
000591.SZ
000888.SZ
000796.SZ
300740.SZ
```

## Backfill Result

Round284 backfilled shard14 offset5 limit5 with the stock-basic pre-listing filter enabled.

| Metric | Value |
|---|---:|
| Selected symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods after pre-listing filter | 208 |
| Endpoint requests executed | 624 |
| Pre-listing skipped symbol-periods | 12 |
| Pre-listing endpoint requests avoided | 36 |
| Processed rows | 208 |
| Empty requests | 0 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Quality report rows | 208 |
| Quality report assets | 5 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |

Selected symbols:

```text
002103.SZ
000591.SZ
000888.SZ
000796.SZ
300740.SZ
```

## Aggregate Source Gate

After the Round284 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 87 |
| Aggregate rows | 67,142 |
| Unique symbols | 312 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 307 to 312 unique symbols, but this is still only 31.2% of the 1,000-symbol source gate.

## Factor Outcome

Round284 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional and correct under the current governance. Running financial reporting timeliness IC screens at 312 symbols would repeat the known short-sample and multiple-testing failure mode.

## Decision For Round285

Continue source construction only if the next segment passes aggregate-overlap preview. The route remains useful because:

- overlap preview avoided duplicate endpoint spending;
- stock-basic pre-listing filtering avoided 36 endpoint requests this round;
- true post-filter empty requests stayed at 0;
- standard quality report rows and assets matched the combined multi-symbol summary.

Next allowed direction:

```text
round285_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
```

Blocked shortcuts:

- no candidate generation before 1,000 unique symbols;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no live backfill without stock-basic pre-listing filter;
- no live backfill without aggregate-overlap preview;
- no trusting the standard quality file unless it matches the combined ingest summary.
