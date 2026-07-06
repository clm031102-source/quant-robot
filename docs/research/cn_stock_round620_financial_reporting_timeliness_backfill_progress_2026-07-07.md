# CN Stock Round620 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round620-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 41. This round used shard 41 offset 10 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round619 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round620-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 647 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 170 |
| Row count | 137,351 |
| Unique symbols | 647 |
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
| shard 41 offset 10 limit 5 | 170 | 5 | 0 | 5 |

Selected symbols:

- `301526.SZ`
- `300009.SZ`
- `002527.SZ`
- `000809.SZ`
- `002646.SZ`

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
| Empty requests | 96 |
| Processed rows | 188 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 188 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-21 to 2026-04-28 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round619 Baseline | Round620 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 170 | 171 |
| Row count | 137,351 | 138,290 |
| Unique symbols | 647 | 652 |
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
| shard 41 offset 15 limit 5 | 171 | 5 | 0 | 5 |

Next candidate symbols:

- `002187.SZ`
- `300839.SZ`
- `002828.SZ`
- `300554.SZ`
- `300970.SZ`

## Decision

Round620 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 652-symbol cache. Continue audited net-new backfill only in small windows, with shard 41 offset 15 limit 5 as the next candidate window.
