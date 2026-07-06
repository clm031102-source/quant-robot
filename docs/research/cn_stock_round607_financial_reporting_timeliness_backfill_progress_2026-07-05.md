# CN Stock Round607 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round607-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 38. This round used shard 38 offset 5 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round606 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round607-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 38 offset 5 limit 5 | 157 | 5 | 0 | 5 |

Selected symbols:

- `002958.SZ`
- `000911.SZ`
- `002567.SZ`
- `600489.SH`
- `002236.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 204 |
| Pre-listing skipped symbol-periods | 16 |
| Endpoint requests | 612 |
| Pre-listing skipped endpoint requests | 48 |
| Empty requests | 4 |
| Processed rows | 204 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round606 Baseline | Round607 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 157 | 158 |
| Row count | 124,091 | 125,113 |
| Unique symbols | 582 | 587 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round607 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 587-symbol cache. Continue audited net-new backfill only in small windows, with shard 38 offset 10 limit 5 as the next candidate window.
