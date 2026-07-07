# CN Stock Round632 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round632-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round631. This round used shard 44 offset 15 limit 5, reran the aggregate source audit, confirmed shard 44 exhaustion, and previewed the next net-new shard. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round631 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round632-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 707 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 182 |
| Row count | 149,979 |
| Unique symbols | 707 |
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
| shard 44 offset 15 limit 5 | 182 | 5 | 0 | 5 |

Selected symbols:

- `002149.SZ`
- `002526.SZ`
- `002229.SZ`
- `002051.SZ`
- `300133.SZ`

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
| Ann date range | 2015-04-14 to 2026-04-28 |

## Post-Backfill Source Audit

| Metric | Round631 After Backfill | Round632 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 182 | 183 |
| Row count | 149,979 | 151,070 |
| Unique symbols | 707 | 712 |
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
| shard 44 offset 20 limit 5 | 183 | 0 | 0 | 0 |
| shard 45 offset 0 limit 5 | 183 | 5 | 0 | 5 |

Shard 44 is exhausted. Next candidate symbols:

- `300947.SZ`
- `603787.SH`
- `300192.SZ`
- `002053.SZ`
- `600706.SH`

## Decision

Round632 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving from exhausted shard 44 to shard 45 offset 0 limit 5. Do not preregister or test factors from the current cache.
