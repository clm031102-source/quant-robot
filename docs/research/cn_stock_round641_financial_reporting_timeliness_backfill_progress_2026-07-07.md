# CN Stock Round641 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round641-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round640. This round used shard 47 offset 0 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round640 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round641-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 752 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 191 |
| Row count | 159,342 |
| Unique symbols | 752 |
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
| shard 47 offset 0 limit 5 | 191 | 5 | 0 | 5 |

Selected symbols:

- `002811.SZ`
- `002670.SZ`
- `600368.SH`
- `002065.SZ`
- `605499.SH`

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
| Empty requests | 58 |
| Processed rows | 202 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 202 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-24 to 2026-04-23 |

The empty request count is elevated versus Round640, but readiness and quality blockers remain `[]`. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round640 After Backfill | Round641 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 191 | 192 |
| Row count | 159,342 | 160,366 |
| Unique symbols | 752 | 757 |
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
| shard 47 offset 5 limit 5 | 192 | 5 | 0 | 5 |

Next candidate symbols:

- `002774.SZ`
- `002104.SZ`
- `002565.SZ`
- `605108.SH`
- `002722.SZ`

## Decision

Round641 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 47 offset 5 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
