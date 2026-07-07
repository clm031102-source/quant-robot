# CN Stock Round648 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round648-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round647. This round used shard 48 offset 15 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round647 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round648-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 787 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 198 |
| Row count | 166,684 |
| Unique symbols | 787 |
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
| shard 48 offset 15 limit 5 | 198 | 5 | 0 | 5 |

Selected symbols:

- `002254.SZ`
- `000863.SZ`
- `002219.SZ`
- `002788.SZ`
- `300046.SZ`

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
| Empty requests | 8 |
| Processed rows | 221 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 221 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-16 to 2026-04-28 |

The empty request count fell to 8, but the quality report recorded 1 duplicate row while still passing with blockers `[]`. Keep the duplicate-row item visible as source-QA evidence for later aggregation checks. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round647 After Backfill | Round648 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 198 | 199 |
| Row count | 166,684 | 167,791 |
| Unique symbols | 787 | 792 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 48 offset 20 limit 5 previewed as empty, so the next net-new window advances to shard 49 offset 0 limit 5.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 49 offset 0 limit 5 | 199 | 5 | 0 | 5 |

Next candidate symbols:

- `600058.SH`
- `600082.SH`
- `002522.SZ`
- `001236.SZ`
- `002798.SZ`

## Decision

Round648 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 49 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
