# CN Stock Round613 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-06

Branch: `codex/data-pipeline-financial-timeliness-round613-20260706`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 39. This round used shard 39 offset 15 limit 5, finished the available shard 39 symbol window, and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round612 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round613-20260706` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 39 offset 15 limit 5 | 163 | 5 | 0 | 5 |

Selected symbols:

- `600895.SH`
- `002395.SZ`
- `002647.SZ`
- `300163.SZ`
- `000921.SZ`

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
| Empty requests | 9 |
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
| Ann date range | 2015-04-24 to 2026-04-28 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round612 Baseline | Round613 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 163 | 164 |
| Row count | 130,045 | 131,147 |
| Unique symbols | 612 | 617 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

| Preview | Financial roots | Symbols | Existing | Net-new | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| shard 39 offset 20 limit 5 | 164 | 0 | 0 | 0 | shard 39 complete |
| shard 40 offset 0 limit 5 | 164 | 5 | 0 | 5 | next candidate |

Next candidate symbols:

- `000969.SZ`
- `002158.SZ`
- `002228.SZ`
- `000928.SZ`
- `002343.SZ`

## Decision

Round613 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 617-symbol cache. Continue audited net-new backfill only in small windows, moving to shard 40 offset 0 limit 5 as the next candidate window.
