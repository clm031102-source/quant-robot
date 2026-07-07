# CN Stock Round652 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round652-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round651. This round used shard 49 offset 15 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round651 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round652-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 807 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 202 |
| Row count | 171,022 |
| Unique symbols | 807 |
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
| shard 49 offset 15 limit 5 | 202 | 5 | 0 | 5 |

Selected symbols:

- `600749.SH`
- `301371.SZ`
- `001203.SZ`
- `002486.SZ`
- `300441.SZ`

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
| Empty requests | 137 |
| Processed rows | 175 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 175 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-22 to 2026-04-30 |

The quality report passed with blockers `[]`, 0 duplicate rows, and 0 missing asset-id rows. The 137 empty requests are high for this run family and should remain visible as a source-QA watch item. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round651 After Backfill | Round652 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 202 | 203 |
| Row count | 171,022 | 171,893 |
| Unique symbols | 807 | 812 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 49 offset 20 limit 5 previewed as empty, so the next net-new window advances to shard 50 offset 0 limit 5.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 50 offset 0 limit 5 | 203 | 5 | 0 | 5 |

Next candidate symbols:

- `002342.SZ`
- `300665.SZ`
- `301595.SZ`
- `600886.SH`
- `600461.SH`

## Decision

Round652 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 50 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
