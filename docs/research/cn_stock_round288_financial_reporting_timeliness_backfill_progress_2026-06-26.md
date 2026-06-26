# CN Stock Round288 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round288-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round288 started from the Round287 closeout state:

- last completed round: 287
- next round: 288
- next direction: `round288_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status: cleared
- CN data manifest: review_required with no hard blockers
- manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage

The source gate still requires at least 1,000 unique symbols before financial reporting timeliness candidate generation. This round therefore performed source construction only.

## Pre-Run Overlap Preview

The live endpoint segment was checked before spending Tushare requests:

| Metric | Value |
|---|---:|
| Shard id | 15 |
| Symbol offset | 5 |
| Symbol limit | 5 |
| Existing symbols | 1 |
| Net-new symbols | 4 |
| Net-new ratio | 80% |
| Financial roots scanned | 90 |

Preview symbols:

```text
002086.SZ
000088.SZ
000543.SZ
600792.SH
000937.SZ
```

The existing symbol was:

```text
000088.SZ
```

Because the preview found exactly 80% net-new coverage, the route remained above the scan-ahead trigger. To avoid repeated live endpoint spend, Round288 split the contiguous block into two net-new subsegments and skipped `000088.SZ`.

## Backfill Result

Round288 backfilled only the four net-new symbols with the stock-basic pre-listing filter enabled.

| Segment | Symbols | Planned Symbol-Periods | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---:|---|
| shard15 offset5 limit1 | 1 | 44 | 132 | 44 | 0 | 0 | passed |
| shard15 offset7 limit3 | 3 | 132 | 396 | 132 | 0 | 0 | passed |
| total | 4 | 176 | 528 | 176 | 0 | 0 | passed |

Selected net-new symbols:

```text
002086.SZ
000543.SZ
600792.SH
000937.SZ
```

Quality summary:

| Metric | Value |
|---|---:|
| Quality report rows | 176 |
| Quality report assets | 4 |
| Required column groups passing | 2 / 2 |
| Missing asset id rows | 0 |
| Duplicate rows | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Already-covered symbols skipped before live requests | 1 |

## Aggregate Source Gate

After the Round288 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 92 |
| Aggregate rows | 71,099 |
| Unique symbols | 331 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 327 to 331 unique symbols, but this is still only 33.1% of the 1,000-symbol source gate.

## Factor Outcome

Round288 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional and correct under the current governance. Running financial reporting timeliness IC screens at 331 symbols would repeat the known short-sample, regime, and multiple-testing failure modes.

## Decision For Round289

Continue source construction only if the next segment passes aggregate-overlap preview. The route remains useful because:

- overlap preview prevented repeated live requests for `000088.SZ`;
- all four live-requested symbols were net-new;
- true post-filter empty requests stayed at 0;
- required PIT statement fields passed 2 / 2;
- standard quality report rows and assets matched the net-new ingest result.

Next allowed direction:

```text
round289_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
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
