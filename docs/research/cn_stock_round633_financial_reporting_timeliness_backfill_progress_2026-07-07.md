# CN Stock Round633 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round633-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round632. This round used shard 45 offset 0 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round632 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round633-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 712 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 183 |
| Row count | 151,070 |
| Unique symbols | 712 |
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
| shard 45 offset 0 limit 5 | 183 | 5 | 0 | 5 |

Selected symbols:

- `300947.SZ`
- `603787.SH`
- `300192.SZ`
- `002053.SZ`
- `600706.SH`

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
| Empty requests | 59 |
| Processed rows | 204 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 204 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-24 to 2026-04-29 |

The duplicate row did not create a blocker for this source-only shard run, but it remains a source-QA item before any future factor construction. Factor work remains blocked by the aggregate source gate.

## Post-Backfill Source Audit

| Metric | Round632 After Backfill | Round633 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 183 | 184 |
| Row count | 151,070 | 152,092 |
| Unique symbols | 712 | 717 |
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
| shard 45 offset 5 limit 5 | 184 | 5 | 0 | 5 |

Next candidate symbols:

- `001328.SZ`
- `002110.SZ`
- `002345.SZ`
- `002685.SZ`
- `002282.SZ`

## Decision

Round633 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, with shard 45 offset 5 limit 5 as the next candidate window. Do not preregister or test factors from the current cache.
