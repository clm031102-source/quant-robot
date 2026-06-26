# CN Stock Round289 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round289-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup And Review Gate

Round289 started only after the Round286-288 three-round review was written and wired into the startup gate.

- last completed round before this run: 288
- next direction at startup: `round289_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status after review wiring: cleared
- CN data manifest: review_required with no hard blockers
- manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage

The source gate still requires at least 1,000 unique symbols before financial reporting timeliness candidate generation. This round therefore performed source construction only.

## Pre-Run Overlap Preview And Scan Ahead

The first natural continuation block was shard15 offset10 limit5. It failed the 80% net-new threshold:

| Metric | Value |
|---|---:|
| Shard id | 15 |
| Symbol offset | 10 |
| Symbol limit | 5 |
| Existing symbols | 2 |
| Net-new symbols | 3 |
| Net-new ratio | 60% |
| Financial roots scanned | 92 |

Net-new symbols in the rejected block:

```text
002075.SZ
002201.SZ
601698.SH
```

Already-covered symbols in the rejected block:

```text
000035.SZ
000403.SZ
```

Because the net-new ratio was below 80%, Round289 scanned ahead before spending live endpoint budget. The next block, shard15 offset15 limit5, passed the threshold:

| Metric | Value |
|---|---:|
| Shard id | 15 |
| Symbol offset | 15 |
| Symbol limit | 5 |
| Existing symbols | 1 |
| Net-new symbols | 4 |
| Net-new ratio | 80% |
| Financial roots scanned | 92 |

Net-new symbols:

```text
002214.SZ
000576.SZ
000799.SZ
000698.SZ
```

Already-covered symbol skipped before live requests:

```text
000417.SZ
```

## Backfill Result

Round289 backfilled only the four net-new symbols with the stock-basic pre-listing filter enabled. The block was split around the existing symbol.

| Segment | Symbols | Planned Symbol-Periods | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---:|---|
| shard15 offset15 limit3 | 3 | 132 | 396 | 132 | 24 | 0 | passed |
| shard15 offset19 limit1 | 1 | 44 | 132 | 48 | 3 | 4 | passed |
| total | 4 | 176 | 528 | 180 | 27 | 4 | passed |

Selected net-new symbols:

```text
002214.SZ
000576.SZ
000799.SZ
000698.SZ
```

Quality summary:

| Metric | Value |
|---|---:|
| Quality report rows | 180 |
| Quality report assets | 4 |
| Required column groups passing | 2 / 2 |
| Missing asset id rows | 0 |
| Duplicate rows | 4 |
| Pre-listing endpoint requests avoided | 0 |
| Already-covered symbols skipped before live requests | 1 |
| Empty endpoint responses after pre-listing filter | 27 |

The new warning versus Rounds286-288 is that empty responses returned to a non-zero level and one symbol (`000698.SZ`) produced four duplicate rows. The PIT readiness checks still passed, but future factor-matrix construction must deduplicate by symbol, report period, announcement date, and source priority before any candidate screen.

## Aggregate Source Gate

After the Round289 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 94 |
| Aggregate rows | 71,955 |
| Unique symbols | 335 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 331 to 335 unique symbols, but this is still only 33.5% of the 1,000-symbol source gate.

## Factor Outcome

Round289 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional and correct under the current governance. Running financial reporting timeliness IC screens at 335 symbols would repeat the known short-sample, regime, and multiple-testing failure modes.

## Decision For Round290

Continue source construction only if the next segment passes aggregate-overlap preview. The route remains useful because:

- the offset10 preview prevented live spend on a 60% net-new block;
- scan-ahead found an 80% net-new block;
- the live backfill skipped `000417.SZ` before spending endpoint budget;
- the selected segment added four net-new symbols and lifted aggregate coverage to 335.

Additional watch items for Round290:

- keep scan-ahead mandatory when preview net-new ratio is below 80%;
- continue splitting around existing symbols before live requests;
- treat non-zero empty responses as a source-quality warning, not a blocker by itself;
- track and remove duplicate rows before any future factor matrix;
- continue to block candidate generation until the 1,000-symbol source gate clears.

Next allowed direction:

```text
round290_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_overlap_preview_empty_response_and_duplicate_row_watch_until_1000_symbols
```

Blocked shortcuts:

- no candidate generation before 1,000 unique symbols;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no live backfill without stock-basic pre-listing filter;
- no live backfill without aggregate-overlap preview;
- no live spend on blocks below 80% net-new without scan-ahead.
