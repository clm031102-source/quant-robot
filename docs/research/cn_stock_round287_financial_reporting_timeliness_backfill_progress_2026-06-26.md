# CN Stock Round287 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round287-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round287 started from the Round286 closeout state:

- last completed round: 286
- next round: 287
- next direction: `round287_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status: cleared
- CN data manifest: review_required with no hard blockers
- manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage

The source gate still requires at least 1,000 unique symbols before financial reporting timeliness candidate generation. This round therefore performed source construction only.

## Pre-Run Overlap Preview

The live endpoint segment was checked before spending Tushare requests:

| Metric | Value |
|---|---:|
| Shard id | 15 |
| Symbol offset | 0 |
| Symbol limit | 5 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |
| Financial roots scanned | 89 |

Expected net-new symbols:

```text
000789.SZ
001205.SZ
000625.SZ
301215.SZ
000589.SZ
```

Because the preview found 5 / 5 net-new symbols, no scan-ahead was required.

## Backfill Result

Round287 backfilled shard15 offset0 limit5 with the stock-basic pre-listing filter enabled.

| Metric | Value |
|---|---:|
| Selected symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods after pre-listing filter | 167 |
| Endpoint requests executed | 501 |
| Pre-listing skipped symbol-periods | 53 |
| Pre-listing endpoint requests avoided | 159 |
| Processed rows | 167 |
| Empty requests | 0 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Quality report rows | 167 |
| Quality report assets | 5 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |

Selected symbols:

```text
000789.SZ
001205.SZ
000625.SZ
301215.SZ
000589.SZ
```

## Aggregate Source Gate

After the Round287 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 90 |
| Aggregate rows | 70,209 |
| Unique symbols | 327 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 322 to 327 unique symbols, but this is still only 32.7% of the 1,000-symbol source gate.

## Factor Outcome

Round287 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional and correct under the current governance. Running financial reporting timeliness IC screens at 327 symbols would repeat the known short-sample, regime, and multiple-testing failure modes.

## Decision For Round288

Continue source construction only if the next segment passes aggregate-overlap preview. The route remains useful because:

- overlap preview confirmed all five symbols were net-new before live requests;
- stock-basic pre-listing filtering saved 159 endpoint requests;
- true post-filter empty requests stayed at 0;
- required PIT statement fields passed 2 / 2;
- standard quality report rows and assets matched the multi-symbol ingest result.

Next allowed direction:

```text
round288_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
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
