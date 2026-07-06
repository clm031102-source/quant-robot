# CN Stock Round614 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-06

Branch: `codex/data-pipeline-financial-timeliness-round614-20260706`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 40. This round used shard 40 offset 0 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round613 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round614-20260706` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 40 offset 0 limit 5 | 164 | 5 | 0 | 5 |

Selected symbols:

- `000969.SZ`
- `002158.SZ`
- `002228.SZ`
- `000928.SZ`
- `002343.SZ`

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
| Empty requests | 3 |
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
| Ann date range | 2015-04-21 to 2026-04-28 |
| Parquet files | 672 |

## Post-Backfill Source Audit

| Metric | Round613 Baseline | Round614 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 164 | 165 |
| Row count | 131,147 | 132,258 |
| Unique symbols | 617 | 622 |
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
| shard 40 offset 5 limit 5 | 165 | 5 | 0 | 5 |

Next candidate symbols:

- `300917.SZ`
- `603129.SH`
- `002607.SZ`
- `002015.SZ`
- `002627.SZ`

## Decision

Round614 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 622-symbol cache. Continue audited net-new backfill only in small windows, with shard 40 offset 5 limit 5 as the next candidate window after the Round615 two-reviewer checkpoint.
