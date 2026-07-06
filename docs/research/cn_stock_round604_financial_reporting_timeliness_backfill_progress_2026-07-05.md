# CN Stock Round604 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round604-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill on shard 37. The initial shard 37 offset 10 limit 5 preview found one already-covered symbol, so this round avoided duplicate provider work by splitting the run into net-new-only windows: shard 37 offset 10 limit 3 and shard 37 offset 14 limit 1. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round603 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round604-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 37 offset 10 limit 5 | 152 | 5 | 1 | 4 |
| shard 37 offset 10 limit 3 | 152 | 3 | 0 | 3 |
| shard 37 offset 14 limit 1 | 152 | 1 | 0 | 1 |

Existing symbol skipped:

- `000158.SZ`

Backfilled symbols:

- `002500.SZ`
- `603708.SH`
- `600106.SH`
- `603156.SH`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Net-new symbols | 4 |
| Planned symbol-periods | 176 |
| Active symbol-periods | 157 |
| Pre-listing skipped symbol-periods | 19 |
| Endpoint requests | 471 |
| Pre-listing skipped endpoint requests | 57 |
| Empty requests | 0 |
| Processed rows | 157 |
| Duplicate rows in quality reports | 0 |
| Required column groups passing | 2 / 2 in both runs |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round603 Baseline | Round604 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 152 | 154 |
| Row count | 121,602 | 122,396 |
| Unique symbols | 569 | 573 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round604 expanded the local source by four net-new symbols while avoiding a known duplicate, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 573-symbol cache. Continue audited net-new backfill only in small windows, with shard 37 offset 15 limit 5 as the next candidate window.
