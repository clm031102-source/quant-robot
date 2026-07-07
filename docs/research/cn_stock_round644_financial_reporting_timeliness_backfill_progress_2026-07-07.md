# CN Stock Round644 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round644-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round643. This round used shard 47 offset 15 limit 5, reran the aggregate source audit, and scanned for the next net-new window after the shard 47 tail was exhausted. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round643 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round644-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 767 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 194 |
| Row count | 162,490 |
| Unique symbols | 767 |
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
| shard 47 offset 15 limit 5 | 194 | 5 | 0 | 5 |

Selected symbols:

- `002891.SZ`
- `600988.SH`
- `002351.SZ`
- `002255.SZ`
- `002107.SZ`

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
| Empty requests | 14 |
| Processed rows | 217 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 217 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-09 to 2026-04-24 |

The empty request count remains a source-QA watch item, but it continued to improve versus Rounds642-643. Readiness and quality blockers remain `[]`. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round643 After Backfill | Round644 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 194 | 195 |
| Row count | 162,490 | 163,568 |
| Unique symbols | 767 | 772 |
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
| shard 47 offset 20 limit 5 | 195 | 0 | 0 | 0 |
| shard 48 offset 0 limit 5 | 195 | 5 | 0 | 5 |
| shard 48 offset 5 limit 5 | 195 | 5 | 0 | 5 |

Next candidate symbols for shard 48 offset 0:

- `300915.SZ`
- `002264.SZ`
- `300240.SZ`
- `300335.SZ`
- `000727.SZ`

Shard 48 offset 5 was also previewed only as a scan-ahead check and should not be run before shard 48 offset 0 is completed:

- `000736.SZ`
- `301078.SZ`
- `002372.SZ`
- `002299.SZ`
- `603789.SH`

## Decision

Round644 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 48 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
