# CN Stock Round684 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round684-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round683. This round used shard 57 offset 15 limit 5, reran explicit all-root aggregate source audits, confirmed the shard 57 boundary, and previewed the next net-new shard. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round683 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round684-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 967 / 1,000 unique symbols using `--financial-root data\processed` |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 234 |
| Row count | 204,787 |
| Unique symbols | 967 |
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
| shard 57 offset 15 limit 5 | 234 | 5 | 0 | 5 |

Selected symbols:

- `600816.SH`
- `300616.SZ`
- `002035.SZ`
- `002182.SZ`
- `300201.SZ`

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
| Empty requests | 11 |
| Processed rows | 245 |
| Duplicate rows in quality report | 28 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 245 |
| Missing asset-id rows | 0 |
| Duplicate rows | 28 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-10 to 2026-04-29 |

The quality report passed with blockers `[]`, 28 duplicate rows, and 0 missing asset-id rows. Empty requests were 11 for this slice. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round683 After Backfill | Round684 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 234 | 235 |
| Row count | 204,787 | 205,911 |
| Unique symbols | 967 | 972 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Boundary And Next Window Preview

Shard 57 offset 20 limit 5 returned 0 symbols, confirming the shard 57 boundary. Shard 58 offset 0 limit 5 then previewed as 5 / 5 net-new.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 57 offset 20 limit 5 | 235 | 0 | 0 | 0 |
| shard 58 offset 0 limit 5 | 235 | 5 | 0 | 5 |

Next candidate symbols:

- `002374.SZ`
- `002062.SZ`
- `300291.SZ`
- `603506.SH`
- `300329.SZ`

## Decision

Round684 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 58 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
