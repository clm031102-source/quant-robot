# CN Stock Round283 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round283-financial-timeliness-20260626`
- Scope: CN A-share stock cross-sectional alpha research
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round283 started from the Round282 closeout state:

- last completed round: 282
- next round: 283
- next direction: `round283_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols`
- startup gate status: cleared
- CN data manifest: review-required only, with no hard startup blockers

The purpose of this round was not candidate generation. The source gate still required at least 1,000 unique symbols before any financial reporting timeliness factor IC screen or portfolio grid could be considered.

## Pre-Run Overlap Preview

The live endpoint segment was checked before spending Tushare requests:

- shard: 14
- symbol offset: 0
- symbol limit: 5
- expected existing symbols: 0
- expected net-new symbols: 5 / 5
- expected net-new symbols: `000628.SZ`, `000892.SZ`, `001914.SZ`, `002999.SZ`, `002105.SZ`

This cleared the Round281/Round282 efficiency rule: do not blindly backfill symbols that already exist in the aggregate PIT statement source.

## Backfill Result

Round283 backfilled shard14 offset0 limit5 with the stock-basic pre-listing filter enabled.

| Metric | Value |
|---|---:|
| Selected symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods after pre-listing filter | 198 |
| Endpoint requests executed | 594 |
| Pre-listing skipped symbol-periods | 22 |
| Pre-listing endpoint requests avoided | 66 |
| Processed rows | 198 |
| Empty requests | 0 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Quality report rows | 198 |
| Quality report assets | 5 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |

Selected symbols:

```text
000628.SZ
000892.SZ
001914.SZ
002999.SZ
002105.SZ
```

## Aggregate Source Gate

After the Round283 segment, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 86 |
| Aggregate rows | 66,098 |
| Unique symbols | 307 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 302 to 307 unique symbols, but this is still only 30.7% of the 1,000-symbol source gate.

## Bug Found And Fixed

During closeout, the standard file `financial_statement_quality_report.json` was found to be misleading for multi-symbol backfills that use the stock-basic pre-listing filter.

Root cause:

- the shard script may call the statement ingest separately for each symbol when pre-listing skips are present;
- each ingest writes `financial_statement_quality_report.json`;
- the final per-symbol ingest overwrote the standard quality file;
- the in-memory combined result and shard backfill report were correct, but the standalone quality file could show only the last symbol.

Fix:

- added a regression test that fails when the standard quality file does not match the combined ingest summary;
- updated `scripts/run_financial_statement_shard_backfill.py` so `_write_report()` writes the combined quality report to `financial_statement_quality_report.json`;
- refreshed the Round283 generated quality report locally; it now shows 198 rows and 5 assets.

This matters because future source audits and manual reviews should not trust a stale last-symbol quality summary.

## Factor Outcome

Round283 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional. At 307 unique symbols, financial reporting timeliness factor generation remains blocked by the source gate.

## Decision For Round284

Continue the same source-construction route only if the next segment passes overlap preview.

Required before Round284 live requests:

- run startup gate with Round283 marked complete;
- run aggregate-overlap preview before any live endpoint calls;
- keep the stock-basic pre-listing filter mandatory;
- reject candidate generation, short-sample IC screens, and portfolio grids until the 1,000-symbol source gate clears;
- verify the standard `financial_statement_quality_report.json` matches the combined ingest summary for multi-symbol backfills.

Next allowed direction:

```text
round284_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
```
