# CN Stock Round600 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round600-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 36. This round used shard 36 offset 10 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round599 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round600-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 36 offset 10 limit 5 | 148 | 5 | 0 | 5 |

Selected symbols:

- `600295.SH`
- `000826.SZ`
- `301188.SZ`
- `002252.SZ`
- `002414.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 193 |
| Pre-listing skipped symbol-periods | 27 |
| Endpoint requests | 579 |
| Pre-listing skipped endpoint requests | 81 |
| Empty requests | 0 |
| Processed rows | 193 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round599 Baseline | Round600 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 148 | 149 |
| Row count | 117,309 | 118,289 |
| Unique symbols | 549 | 554 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round600 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 554-symbol cache. Continue audited net-new backfill only in small windows, with shard 36 offset 15 limit 5 as the next candidate window.
