# CN Stock Round609 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-06

Branch: `codex/data-pipeline-financial-timeliness-round609-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 38. This round used shard 38 offset 15 limit 5, finished the available shard 38 symbol window, and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round608 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round609-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 38 offset 15 limit 5 | 159 | 5 | 0 | 5 |

Selected symbols:

- `002468.SZ`
- `002700.SZ`
- `000670.SZ`
- `000656.SZ`
- `300622.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 212 |
| Pre-listing skipped symbol-periods | 8 |
| Endpoint requests | 636 |
| Pre-listing skipped endpoint requests | 24 |
| Empty requests | 1 |
| Processed rows | 212 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 212 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-14 to 2026-04-28 |
| Parquet files | 648 |

## Post-Backfill Source Audit

| Metric | Round608 Baseline | Round609 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 159 | 160 |
| Row count | 125,982 | 127,059 |
| Unique symbols | 592 | 597 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

| Preview | Financial roots | Symbols | Existing | Net-new | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| shard 38 offset 20 limit 5 | 160 | 0 | 0 | 0 | shard 38 complete |
| shard 39 offset 0 limit 5 | 160 | 5 | 0 | 5 | next candidate |

Next candidate symbols:

- `002271.SZ`
- `002157.SZ`
- `301533.SZ`
- `000902.SZ`
- `301025.SZ`

## Decision

Round609 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 597-symbol cache. Continue audited net-new backfill only in small windows, moving to shard 39 offset 0 limit 5 as the next candidate window.
