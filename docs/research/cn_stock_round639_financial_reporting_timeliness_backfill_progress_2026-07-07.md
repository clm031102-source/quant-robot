# CN Stock Round639 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round639-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round638. This round used shard 46 offset 10 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round638 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round639-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 742 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`; pending factor-batch branch noted separately |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 189 |
| Row count | 157,176 |
| Unique symbols | 742 |
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
| shard 46 offset 10 limit 5 | 189 | 5 | 0 | 5 |

Selected symbols:

- `600688.SH`
- `600871.SH`
- `300700.SZ`
- `600883.SH`
- `603779.SH`

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
| Empty requests | 17 |
| Processed rows | 216 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 216 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-24 to 2026-04-29 |

## Post-Backfill Source Audit

| Metric | Round638 After Backfill | Round639 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 189 | 190 |
| Row count | 157,176 | 158,269 |
| Unique symbols | 742 | 747 |
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
| shard 46 offset 15 limit 5 | 190 | 5 | 0 | 5 |

Next candidate symbols:

- `002327.SZ`
- `603025.SH`
- `600620.SH`
- `302132.SZ`
- `600482.SH`

## Decision

Round639 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, with shard 46 offset 15 limit 5 as the next candidate window. Do not preregister or test factors from the current cache.
