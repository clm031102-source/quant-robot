# CN Stock Round634 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round634-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round633. This round used shard 45 offset 5 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round633 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round634-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 717 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 184 |
| Row count | 152,092 |
| Unique symbols | 717 |
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
| shard 45 offset 5 limit 5 | 184 | 5 | 0 | 5 |

Selected symbols:

- `001328.SZ`
- `002110.SZ`
- `002345.SZ`
- `002685.SZ`
- `002282.SZ`

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
| Empty requests | 87 |
| Processed rows | 192 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 192 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-22 to 2026-04-25 |

## Post-Backfill Source Audit

| Metric | Round633 After Backfill | Round634 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 184 | 185 |
| Row count | 152,092 | 153,062 |
| Unique symbols | 717 | 722 |
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
| shard 45 offset 10 limit 5 | 185 | 5 | 0 | 5 |

Next candidate symbols:

- `300576.SZ`
- `001325.SZ`
- `600868.SH`
- `600283.SH`
- `002596.SZ`

## Decision

Round634 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, with shard 45 offset 10 limit 5 as the next candidate window. Do not preregister or test factors from the current cache.
