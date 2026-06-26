# CN Stock Round280 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round280-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round280 startup gates cleared for source construction:

- Quant PM startup gate: ready, no blockers
- CN stock startup gate: cleared, no blockers
- CN data manifest: review_required with no blockers
- Manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage
- last completed round before execution: 279
- next round before execution: 280
- required source gate: 1,000 unique symbols before financial reporting timeliness factor candidate generation
- final holdout: blocked

This round continued source construction only. It did not generate, screen, or promote any factor.

## Backfill Work

Round280 completed the first half of shard 12 with the stock-basic pre-listing filter enabled:

| Segment | Symbols | Planned Endpoint Requests | Active Endpoint Requests | Pre-Listing Requests Skipped | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| shard12 offset0 limit5 | 5 | 660 | 660 | 0 | 220 | 0 | 0 | passed |
| shard12 offset5 limit5 | 5 | 660 | 660 | 0 | 223 | 0 | 3 | passed |
| total | 10 | 1,320 | 1,320 | 0 | 443 | 0 | 3 | passed |

Symbols fetched:

```text
000876.SZ, 000975.SZ, 000977.SZ, 600636.SH, 000856.SZ,
000590.SZ, 002570.SZ, 002095.SZ, 002010.SZ, 000593.SZ
```

Both subsegments passed required PIT statement readiness:

- required column groups passing: 2 / 2
- readiness blockers: none
- offset0 readiness files scanned: 674
- offset5 readiness files scanned: 674

The stock-basic list-date filter was mandatory and ran. It skipped no requests in this round because all 10 symbols were already listed before the 2015 analysis start date. The true post-filter empty-request count was still 0.

## Aggregate Source Audit

After adding Round280 shard12 offset0 and offset5 processed roots, the aggregate source audit reported:

| Metric | Value |
|---|---:|
| Sources | 79 |
| Aggregate rows | 58,982 |
| Aggregate unique symbols | 277 |
| Minimum required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains:

```text
unique_symbol_count_below_minimum
```

Coverage increased from 267 after Round279 to 277 after Round280. The 10 fetched symbols produced 10 incremental unique symbols in the aggregate union.

## Quality Notes

Round280 validates two separate points:

- The pre-listing filter is still required even when it has no skip savings in a specific segment.
- Empty endpoint waste was 0, but duplicate monitoring remains active because offset5 contained 3 duplicate rows.

The duplicate rows did not block readiness, but they remain a source-quality watch item before any future factor candidate generation.

## Factor Outcome

Round280 produced:

- new factor names: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional. The source gate still blocks factor generation before 1,000 unique symbols. Running IC screens, portfolio grids, or promotion checks at 277 symbols would repeat a known short-sample overfitting failure mode.

## Direction Decision

Continue financial reporting timeliness source construction with the stock-basic pre-listing filter mandatory.

Reasons to continue:

- aggregate coverage increased by 10 unique symbols;
- both Round280 subsegments passed readiness;
- true empty endpoint requests were 0 after the list-date-aware planner;
- the route still has not reached fair alpha-testing conditions.

Reasons for caution:

- coverage is still only 277 / 1,000 required symbols;
- duplicate rows recurred in offset5 and must remain on the quality watch list;
- this round had no pre-listing skip savings because all symbols were already listed before 2015;
- factor generation remains blocked until the source gate clears.

Round281 should continue shard 12:

```text
shard_id=12, symbol_offset=10, symbol_limit=5
```

Expected next segment:

```text
601628.SH, 000536.SZ, 000031.SZ, 600650.SH, 603813.SH
```

Required command discipline:

```text
--stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic
```

Blocked shortcuts for Round281:

- no financial reporting timeliness candidate generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no backfill without the stock-basic pre-listing filter.
