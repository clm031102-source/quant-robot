# CN Stock Round666 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round666-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round665. This round used shard 53 offset 5 limit 5, reran explicit all-root aggregate source audits, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round665 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round666-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 877 / 1,000 unique symbols using `--financial-root data\processed` |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 216 |
| Row count | 185,840 |
| Unique symbols | 877 |
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
| shard 53 offset 5 limit 5 | 216 | 5 | 0 | 5 |

Selected symbols:

- `002872.SZ`
- `300053.SZ`
- `600128.SH`
- `600007.SH`
- `002585.SZ`

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
| Ann date range | 2015-04-24 to 2026-04-29 |

The quality report passed with blockers `[]`, 0 duplicate rows, and 0 missing asset-id rows. Empty requests were 14 for this slice. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round665 After Backfill | Round666 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 216 | 217 |
| Row count | 185,840 | 186,941 |
| Unique symbols | 877 | 882 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 53 offset 10 limit 5 previewed as 5 / 5 net-new.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 53 offset 10 limit 5 | 217 | 5 | 0 | 5 |

Next candidate symbols:

- `600643.SH`
- `002853.SZ`
- `002032.SZ`
- `002176.SZ`
- `300185.SZ`

## Decision

Round666 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 53 offset 10 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
