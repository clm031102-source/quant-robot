# CN Stock Round640 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round640-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round639. This round used shard 46 offset 15 limit 5, reran the aggregate source audit, detected the empty shard 46 tail, and previewed the next net-new window in shard 47. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round639 and Round507 docs were merged |
| New branch | `codex/data-pipeline-financial-timeliness-round640-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 747 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 190 |
| Row count | 158,269 |
| Unique symbols | 747 |
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
| shard 46 offset 15 limit 5 | 190 | 5 | 0 | 5 |

Selected symbols:

- `002327.SZ`
- `603025.SH`
- `600620.SH`
- `302132.SZ`
- `600482.SH`

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
| Empty requests | 0 |
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
| Ann date range | 2015-04-23 to 2026-04-30 |

The single duplicate row is a data-quality watch item for later source QA. The quality report still passed with blockers `[]`, but this does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round639 After Backfill | Round640 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 190 | 191 |
| Row count | 158,269 | 159,342 |
| Unique symbols | 747 | 752 |
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
| shard 46 offset 20 limit 5 | 191 | 0 | 0 | 0 |
| shard 47 offset 0 limit 5 | 191 | 5 | 0 | 5 |

Shard 46 is exhausted at offset 20. Next candidate symbols:

- `002811.SZ`
- `002670.SZ`
- `600368.SH`
- `002065.SZ`
- `605499.SH`

## Decision

Round640 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 47 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
