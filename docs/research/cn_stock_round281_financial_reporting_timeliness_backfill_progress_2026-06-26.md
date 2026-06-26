# CN Stock Round281 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round281-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round281 startup gates cleared for source construction:

- Quant PM startup gate: ready, no blockers
- CN stock startup gate: cleared, no blockers
- CN data manifest: review_required with no blockers
- Manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage
- last completed round before execution: 280
- next round before execution: 281
- required source gate: 1,000 unique symbols before financial reporting timeliness factor candidate generation
- final holdout: blocked

This round continued source construction only. It did not generate, screen, or promote any factor.

## Backfill Work

Round281 completed the second half of shard 12 with the stock-basic pre-listing filter enabled:

| Segment | Symbols | Planned Endpoint Requests | Active Endpoint Requests | Pre-Listing Requests Skipped | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| shard12 offset10 limit5 | 5 | 660 | 630 | 30 | 210 | 0 | 0 | passed |
| shard12 offset15 limit5 | 5 | 660 | 660 | 0 | 220 | 0 | 0 | passed |
| total | 10 | 1,320 | 1,290 | 30 | 430 | 0 | 0 | passed |

Symbols fetched:

```text
601628.SH, 000536.SZ, 000031.SZ, 600650.SH, 603813.SH,
000829.SZ, 000786.SZ, 000061.SZ, 300022.SZ, 000408.SZ
```

Both subsegments passed required PIT statement readiness:

- required column groups passing: 2 / 2
- readiness blockers: none
- offset10 readiness files scanned: 644
- offset15 readiness files scanned: 674

The stock-basic list-date filter was mandatory and ran. It skipped 10 pre-listing symbol-periods, equal to 30 avoided endpoint requests.

Shard 12 is now complete.

## Aggregate Source Audit

After adding Round281 shard12 offset10 and offset15 processed roots, the aggregate source audit reported:

| Metric | Value |
|---|---:|
| Sources | 81 |
| Aggregate rows | 61,139 |
| Aggregate unique symbols | 284 |
| Minimum required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains:

```text
unique_symbol_count_below_minimum
```

Coverage increased from 277 after Round280 to 284 after Round281. The round fetched 10 symbols, but only 7 were net-new to the aggregate union because the following three symbols were already present in an earlier filtered PIT source:

```text
000031.SZ, 000061.SZ, 000408.SZ
```

This is a method-efficiency warning: future backfill planning should preview expected net-new aggregate symbols before spending endpoint budget.

## Quality Notes

Round281 quality was cleaner than Round280:

- true post-filter empty endpoint requests: 0
- duplicate rows: 0
- readiness blockers: none
- pre-listing filter savings: 30 endpoint requests

The route remains viable, but the overlap with older PIT sources means raw fetched-symbol count is not the same as source-gate progress.

## Factor Outcome

Round281 produced:

- new factor names: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional. The source gate still blocks factor generation before 1,000 unique symbols. Running IC screens, portfolio grids, or promotion checks at 284 symbols would repeat a known short-sample overfitting failure mode.

## Direction Decision

Continue financial reporting timeliness source construction with two additions:

- keep the stock-basic pre-listing filter mandatory;
- add a pre-run aggregate-overlap preview so each new segment estimates net-new source coverage before live endpoint requests.

Reasons to continue:

- aggregate coverage still increased;
- shard 12 is complete;
- both Round281 subsegments passed readiness;
- true empty endpoint requests were 0;
- the route still has not reached fair alpha-testing conditions.

Reasons for caution:

- coverage is still only 284 / 1,000 required symbols;
- 3 of 10 fetched symbols were already present in an earlier filtered PIT source;
- factor generation remains blocked until the source gate clears.

Round282 should start shard 13:

```text
shard_id=13, symbol_offset=0, symbol_limit=5
```

Expected first segment:

```text
002181.SZ, 000597.SZ, 000635.SZ, 002337.SZ, 000703.SZ
```

The new overlap preview tool was run for this segment before the next live backfill:

| Preview Metric | Value |
|---|---:|
| Symbols checked | 5 |
| Already present in aggregate sources | 0 |
| Expected net-new symbols | 5 |
| Expected net-new ratio | 100% |

Preview report:

```text
data\reports\round282_financial_statement_shard13_offset0_overlap_preview_20260626
```

Required command discipline:

```text
--stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic
```

Blocked shortcuts for Round282:

- no financial reporting timeliness candidate generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no backfill without the stock-basic pre-listing filter;
- no blind continuation without previewing aggregate symbol overlap.
