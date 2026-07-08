# CN Stock Round676 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round676-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round675. This round used shard 55 offset 15 limit 5, reran explicit all-root aggregate source audits, and searched for the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round675 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round676-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 927 / 1,000 unique symbols using `--financial-root data\processed` |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 226 |
| Row count | 196,467 |
| Unique symbols | 927 |
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
| shard 55 offset 15 limit 5 | 226 | 5 | 0 | 5 |

Selected symbols:

- `002830.SZ`
- `002736.SZ`
- `600377.SH`
- `002178.SZ`
- `002972.SZ`

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
| Empty requests | 22 |
| Processed rows | 216 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 216 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-22 to 2026-04-28 |

The quality report passed with blockers `[]`, 1 duplicate row, and 0 missing asset-id rows. Empty requests were 22 for this slice. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round675 After Backfill | Round676 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 226 | 227 |
| Row count | 196,467 | 197,543 |
| Unique symbols | 927 | 932 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 55 contains 20 symbols. After shard 55 offset 15 limit 5, shard 55 offset 20 limit 5 is a boundary check and returned 0 symbols. The next actionable preview is shard 56 offset 0 limit 5, which previewed as 5 / 5 net-new.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 55 offset 20 limit 5 | 227 | 0 | 0 | 0 |
| shard 56 offset 0 limit 5 | 227 | 5 | 0 | 5 |

Next candidate symbols:

- `002161.SZ`
- `300883.SZ`
- `002843.SZ`
- `600961.SH`
- `601899.SH`

## Decision

Round676 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 56 offset 0 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
