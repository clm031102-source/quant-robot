# CN Stock Round627 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-07

Branch: `codex/data-pipeline-financial-timeliness-round627-20260707`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round626. This round used shard 43 offset 5 limit 5, reran the aggregate source audit, and previewed the next windows. The sequential shard 43 offset 10 window was mixed, so the next default window moves to shard 43 offset 15 where the preview was 5 / 5 net-new. This round did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round626 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round627-20260707` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 682 / 1,000 unique symbols |
| Sync audit before provider work | no syncable files and no blockers |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 177 |
| Row count | 144,635 |
| Unique symbols | 682 |
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
| shard 43 offset 5 limit 5 | 177 | 5 | 0 | 5 |

Selected symbols:

- `002268.SZ`
- `688287.SH`
- `002204.SZ`
- `002082.SZ`
- `300898.SZ`

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
| Empty requests | 63 |
| Processed rows | 203 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 203 |
| Missing asset-id rows | 0 |
| Duplicate rows | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-24 to 2026-04-30 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round626 After Backfill | Round627 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 177 | 178 |
| Row count | 144,635 | 145,668 |
| Unique symbols | 682 | 687 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

| Preview | Financial roots | Symbols | Existing | Net-new | Next-use decision |
| --- | ---: | ---: | ---: | ---: | --- |
| shard 43 offset 10 limit 5 | 178 | 5 | 2 | 3 | skip as next default because not 5 / 5 net-new |
| shard 43 offset 15 limit 5 | 178 | 5 | 0 | 5 | use next |

Next candidate symbols:

- `300755.SZ`
- `002333.SZ`
- `002234.SZ`
- `601038.SH`
- `000912.SZ`

## Decision

Round627 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 687-symbol cache. Continue audited net-new backfill only in small windows. Keep the 5 / 5 net-new default and use shard 43 offset 15 limit 5 next; revisit the mixed shard 43 offset 10 window only if a later partial-window policy is explicitly chosen.
