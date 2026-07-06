# CN Stock Round601 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round601-20260705`

Scope: finish financial reporting timeliness / PIT statement backfill shard 36. This round used shard 36 offset 15 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round600 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round601-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 36 offset 15 limit 5 | 149 | 5 | 0 | 5 |

Selected symbols:

- `000720.SZ`
- `002304.SZ`
- `000785.SZ`
- `300135.SZ`
- `300483.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 219 |
| Pre-listing skipped symbol-periods | 1 |
| Endpoint requests | 657 |
| Pre-listing skipped endpoint requests | 3 |
| Empty requests | 1 |
| Processed rows | 219 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round600 Baseline | Round601 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 149 | 150 |
| Row count | 118,289 | 119,399 |
| Unique symbols | 554 | 559 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round601 completed shard 36 and expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 559-symbol cache. Continue audited net-new backfill only in small windows, starting shard 37 with a financial-root overlap preview first.
