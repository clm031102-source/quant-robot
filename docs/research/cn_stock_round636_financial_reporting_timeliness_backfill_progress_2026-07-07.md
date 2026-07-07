# CN Stock Round636 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round636-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round635. This round used shard 45 offset 15 limit 5, reran the aggregate source audit, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round635 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round636-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 727 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 186 |
| Row count | 153,965 |
| Unique symbols | 727 |
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
| shard 45 offset 15 limit 5 | 186 | 5 | 0 | 5 |

Selected symbols:

- `601872.SH`
- `301039.SZ`
- `603377.SH`
- `000901.SZ`
- `600018.SH`

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
| Empty requests | 50 |
| Processed rows | 207 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 207 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-29 to 2026-04-29 |

The duplicate row count remains visible for later source QA and does not authorize factor work.

## Post-Backfill Source Audit

| Metric | Round635 After Backfill | Round636 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 186 | 187 |
| Row count | 153,965 | 154,998 |
| Unique symbols | 727 | 732 |
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
| shard 45 offset 20 limit 5 | 187 | 0 | 0 | 0 |
| shard 46 offset 0 limit 5 | 187 | 5 | 0 | 5 |

Next candidate symbols:

- `000899.SZ`
- `600188.SH`
- `603995.SH`
- `000890.SZ`
- `600819.SH`

## Decision

Round636 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Shard 45 is exhausted; continue audited net-new backfill only in small windows, with shard 46 offset 0 limit 5 as the next candidate window. Do not preregister or test factors from the current cache.
