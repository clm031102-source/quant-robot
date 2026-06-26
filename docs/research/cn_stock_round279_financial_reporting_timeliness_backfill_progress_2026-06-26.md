# CN Stock Round279 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round279-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round279 startup gates cleared for source construction:

- Quant PM startup gate: ready, no blockers
- CN stock startup gate: cleared, no blockers
- CN data manifest: review_required with no blockers
- Manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage
- last completed round before execution: 278
- next round before execution: 279
- required source gate: 1,000 unique symbols before financial reporting timeliness factor candidate generation
- final holdout: blocked

This round continued source construction only. It did not generate, screen, or promote any factor.

## Backfill Work

Round279 completed the second half of shard 11 with the stock-basic pre-listing filter enabled:

| Segment | Symbols | Planned Endpoint Requests | Active Endpoint Requests | Pre-Listing Requests Skipped | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| shard11 offset10 limit5 | 5 | 660 | 582 | 78 | 194 | 0 | 0 | passed |
| shard11 offset15 limit5 | 5 | 660 | 660 | 0 | 220 | 0 | 0 | passed |
| total | 10 | 1,320 | 1,242 | 78 | 414 | 0 | 0 | passed |

Symbols fetched:

```text
002012.SZ, 000721.SZ, 002132.SZ, 001213.SZ, 000603.SZ,
000737.SZ, 000807.SZ, 002142.SZ, 300234.SZ, 000523.SZ
```

Both subsegments passed required PIT statement readiness:

- required column groups passing: 2 / 2
- readiness blockers: none
- offset10 readiness files scanned: 596
- offset15 readiness files scanned: 674

Shard 11 is now complete.

## Pre-Listing Filter Result

Round279 was the first real backfill round that required `--stock-basic-path`.

The filter skipped 26 pre-listing statement periods for:

```text
001213.SZ list_date = 2021-09-08
```

Skipped statement periods ran from 2015-03-31 through 2021-06-30. Because each statement period would otherwise request income, balance sheet, and cashflow endpoints, this saved 78 Tushare endpoint requests.

Most importantly, the true post-filter empty-request count was:

```text
0
```

This validates the Round278 root-cause diagnosis: the prior empty-request spike was mostly request-planning waste for later-listed stocks, not a random endpoint failure.

## Tooling Fix

During Round279 evidence review, a reporting bug was found and fixed:

- When `--stock-basic-path` triggered per-symbol ingestion, combined `processed_rows` was correct.
- The nested `ingest.quality_report.summary` still reflected only the final per-symbol ingest.
- This could make a multi-symbol segment look like a one-symbol quality report even when the processed output and readiness audit were correct.

The backfill CLI now combines per-symbol quality summaries across rows, assets, duplicates, blockers, required groups, and date ranges. A regression test now checks that a pre-listing-filtered two-symbol run reports the combined row and asset counts.

## Aggregate Source Audit

After adding Round279 shard11 offset10 and offset15 processed roots, the aggregate source audit reported:

| Metric | Value |
|---|---:|
| Sources | 77 |
| Aggregate rows | 56,760 |
| Aggregate unique symbols | 267 |
| Minimum required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains:

```text
unique_symbol_count_below_minimum
```

Coverage increased from 257 after Round278 to 267 after Round279. The 10 fetched symbols produced 10 incremental unique symbols in the aggregate union.

## Factor Outcome

Round279 produced:

- new factor names: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional. The source gate still blocks factor generation before 1,000 unique symbols. Running IC screens, portfolio grids, or promotion checks at 267 symbols would repeat a known short-sample overfitting failure mode.

## Direction Decision

Continue financial reporting timeliness source construction with the stock-basic pre-listing filter mandatory.

Reasons to continue:

- aggregate coverage increased by 10 unique symbols;
- shard 11 is complete;
- both Round279 subsegments passed readiness;
- pre-listing filtering reduced endpoint waste and eliminated true empty requests in this round;
- the route still has not reached fair alpha-testing conditions.

Reasons for caution:

- coverage is still only 267 / 1,000 required symbols;
- this round proves the filter helps, not that endpoint quality risk is retired forever;
- factor generation remains blocked until the source gate clears.

Round280 should start shard 12:

```text
shard_id=12, symbol_offset=0, symbol_limit=5
```

Expected first segment:

```text
000876.SZ, 000975.SZ, 000977.SZ, 600636.SH, 000856.SZ
```

Required command discipline:

```text
--stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic
```

Blocked shortcuts for Round280:

- no financial reporting timeliness candidate generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no backfill without the stock-basic pre-listing filter.
