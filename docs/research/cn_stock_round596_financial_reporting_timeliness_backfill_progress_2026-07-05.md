# CN Stock Round596 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round596-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 35. This round used shard 35 offset 14 limit 5 and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round595 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round596-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 35 offset 14 limit 5 | 144 | 5 | 0 | 5 |

Selected symbols:

- `002559.SZ`
- `002184.SZ`
- `300522.SZ`
- `300767.SZ`
- `600644.SH`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 198 |
| Pre-listing skipped symbol-periods | 22 |
| Endpoint requests | 594 |
| Pre-listing skipped endpoint requests | 66 |
| Empty requests | 2 |
| Processed rows | 198 |
| Duplicate rows in quality report | 0 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round595 Baseline | Round596 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 144 | 145 |
| Row count | 113,881 | 114,883 |
| Unique symbols | 533 | 538 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round596 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 538-symbol cache. Continue audited net-new backfill only in small windows, with a single-instance process check before each provider-consuming run.
