# CN Stock Round625 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round625-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round624. This round used shard 42 offset 15 limit 5, reran the aggregate source audit, confirmed shard 42 was exhausted at offset 20, and previewed the next net-new window on shard 43. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round624 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round625-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 672 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 175 |
| Row count | 142,450 |
| Unique symbols | 672 |
| Minimum required symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

Gate blocker before provider work:

```text
unique_symbol_count_below_minimum
```

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 42 offset 15 limit 5 | 175 | 5 | 0 | 5 |

Selected symbols:

- `002521.SZ`
- `601007.SH`
- `002593.SZ`
- `600338.SH`
- `600362.SH`

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
| Empty requests | 5 |
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
| Ann date range | 2015-04-23 to 2026-04-28 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round624 After Backfill | Round625 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 175 | 176 |
| Row count | 142,450 | 143,559 |
| Unique symbols | 672 | 677 |
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
| shard 42 offset 20 limit 5 | 176 | 0 | 0 | 0 |
| shard 43 offset 0 limit 5 | 176 | 5 | 0 | 5 |

Next candidate symbols:

- `300057.SZ`
- `002966.SZ`
- `000972.SZ`
- `002696.SZ`
- `600547.SH`

## Decision

Round625 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 677-symbol cache. Shard 42 is exhausted at offset 20, so continue audited net-new backfill only in small windows, with shard 43 offset 0 limit 5 as the next candidate window.
