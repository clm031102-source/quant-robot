# CN Stock Round645 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round645-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round644. This round used shard 48 offset 0 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round644 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round645-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 772 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 195 |
| Row count | 163,568 |
| Unique symbols | 772 |
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
| shard 48 offset 0 limit 5 | 195 | 5 | 0 | 5 |

Selected symbols:

- `300915.SZ`
- `002264.SZ`
- `300240.SZ`
- `300335.SZ`
- `000727.SZ`

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
| Empty requests | 41 |
| Processed rows | 207 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 207 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-09 to 2026-04-29 |

The empty request count moved back up to 41 and should remain visible as a source-QA watch item. Readiness and quality blockers remain `[]`. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round644 After Backfill | Round645 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 195 | 196 |
| Row count | 163,568 | 164,607 |
| Unique symbols | 772 | 777 |
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
| shard 48 offset 5 limit 5 | 196 | 5 | 0 | 5 |

Next candidate symbols:

- `000736.SZ`
- `301078.SZ`
- `002372.SZ`
- `002299.SZ`
- `603789.SH`

## Decision

Round645 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 48 offset 5 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
