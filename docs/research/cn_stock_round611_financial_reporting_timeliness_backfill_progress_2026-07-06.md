# CN Stock Round611 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-06

Branch: `codex/data-pipeline-financial-timeliness-round611-20260706`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 39. This round used shard 39 offset 5 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round610 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round611-20260706` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 39 offset 5 limit 5 | 161 | 5 | 0 | 5 |

Selected symbols:

- `000813.SZ`
- `000818.SZ`
- `300228.SZ`
- `002064.SZ`
- `000718.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 220 |
| Pre-listing skipped symbol-periods | 0 |
| Endpoint requests | 660 |
| Pre-listing skipped endpoint requests | 0 |
| Empty requests | 11 |
| Processed rows | 220 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 220 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-22 to 2026-04-29 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round610 Baseline | Round611 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 161 | 162 |
| Row count | 127,860 | 128,950 |
| Unique symbols | 602 | 607 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 39 offset 10 limit 5 | 162 | 5 | 0 | 5 |

Next candidate symbols:

- `002172.SZ`
- `002589.SZ`
- `002409.SZ`
- `600725.SH`
- `600573.SH`

## Decision

Round611 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 607-symbol cache. Continue audited net-new backfill only in small windows, with shard 39 offset 10 limit 5 as the next candidate window.
