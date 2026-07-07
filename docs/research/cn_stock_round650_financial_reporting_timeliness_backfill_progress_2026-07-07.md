# CN Stock Round650 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round650-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round649. This round used shard 49 offset 5 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round649 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round650-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 797 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 200 |
| Row count | 168,872 |
| Unique symbols | 797 |
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
| shard 49 offset 5 limit 5 | 200 | 5 | 0 | 5 |

Selected symbols:

- `002011.SZ`
- `002167.SZ`
- `002535.SZ`
- `002243.SZ`
- `002060.SZ`

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
| Ann date range | 2015-04-25 to 2026-04-29 |

The quality report passed cleanly with blockers `[]`, 0 empty requests, and 0 duplicate rows. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round649 After Backfill | Round650 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 200 | 201 |
| Row count | 168,872 | 169,977 |
| Unique symbols | 797 | 802 |
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
| shard 49 offset 10 limit 5 | 201 | 5 | 0 | 5 |

Next candidate symbols:

- `300182.SZ`
- `600605.SH`
- `689009.SH`
- `002659.SZ`
- `002218.SZ`

## Decision

Round650 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 49 offset 10 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
