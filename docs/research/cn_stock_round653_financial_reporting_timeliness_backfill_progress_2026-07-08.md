# CN Stock Round653 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round653-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round652. This round used shard 50 offset 0 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round652 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round653-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 812 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 203 |
| Row count | 171,893 |
| Unique symbols | 812 |
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
| shard 50 offset 0 limit 5 | 203 | 5 | 0 | 5 |

Selected symbols:

- `002342.SZ`
- `300665.SZ`
- `301595.SZ`
- `600886.SH`
- `600461.SH`

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
| Empty requests | 118 |
| Processed rows | 187 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 187 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-28 to 2026-04-30 |

The quality report passed with blockers `[]`, 1 duplicate row, and 0 missing asset-id rows. The 118 empty requests and 1 duplicate row should remain visible as source-QA watch items. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round652 After Backfill | Round653 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 203 | 204 |
| Row count | 171,893 | 172,815 |
| Unique symbols | 812 | 817 |
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
| shard 50 offset 5 limit 5 | 204 | 5 | 0 | 5 |

Next candidate symbols:

- `002671.SZ`
- `601866.SH`
- `600686.SH`
- `000903.SZ`
- `601008.SH`

## Decision

Round653 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 50 offset 5 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
