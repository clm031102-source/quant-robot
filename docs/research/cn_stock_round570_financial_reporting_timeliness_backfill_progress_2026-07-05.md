# CN Stock Round570 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round570-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from Round569. This round used shard 25 offset 10 limit 5, ran a live backfill segment with stock-basic pre-listing filtering, and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round569 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round570-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 25 offset 10 limit 5 | 118 | 5 | 0 | 5 |

Selected symbols:

- `002520.SZ`
- `002150.SZ`
- `300067.SZ`
- `300587.SZ`
- `000993.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 212 |
| Pre-listing skipped symbol-periods | 8 |
| Endpoint requests | 636 |
| Pre-listing skipped endpoint requests | 24 |
| Empty requests | 4 |
| Processed rows | 212 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round569 Baseline | Round570 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 118 | 119 |
| Row count | 88,061 | 89,130 |
| Unique symbols | 412 | 417 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round570 expanded the local source by another five symbols, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 417-symbol cache. Continue audited net-new backfill only if provider quota and elapsed time remain acceptable.
