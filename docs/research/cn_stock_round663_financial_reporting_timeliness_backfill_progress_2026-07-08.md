# CN Stock Round663 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round663-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round662. This round used shard 52 offset 10 limit 5, reran explicit all-root aggregate source audits, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round662 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round663-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 862 / 1,000 unique symbols using `--financial-root data\processed` |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 213 |
| Row count | 182,516 |
| Unique symbols | 862 |
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
| shard 52 offset 10 limit 5 | 213 | 5 | 0 | 5 |

Selected symbols:

- `300435.SZ`
- `000733.SZ`
- `000797.SZ`
- `601828.SH`
- `002377.SZ`

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
| Empty requests | 1 |
| Processed rows | 221 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 221 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-21 to 2026-04-29 |

The quality report passed with blockers `[]`, 0 duplicate rows, and 0 missing asset-id rows. Empty requests were 1 for this slice. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round662 After Backfill | Round663 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 213 | 214 |
| Row count | 182,516 | 183,619 |
| Unique symbols | 862 | 867 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 52 offset 15 limit 5 previewed as 5 / 5 net-new.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 52 offset 15 limit 5 | 214 | 5 | 0 | 5 |

Next candidate symbols:

- `002321.SZ`
- `603029.SH`
- `002170.SZ`
- `600825.SH`
- `000919.SZ`

## Decision

Round663 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 52 offset 15 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
