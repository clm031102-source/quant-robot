# CN Stock Round605 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round605-20260705`

Scope: finish financial reporting timeliness / PIT statement backfill shard 37 while avoiding duplicate provider work. The initial shard 37 offset 15 limit 5 preview found one already-covered symbol, so this round ran the net-new-only windows shard 37 offset 15 limit 2 and shard 37 offset 18 limit 2. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup And Review Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round604 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round605-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Single-instance check | no active backfill |
| Two-reviewer checkpoint | GO for small audited data-pipeline backfill only; NO-GO for direct offset 15 limit 5 because `000070.SZ` was already covered |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 37 offset 15 limit 5 | 154 | 5 | 1 | 4 |
| shard 37 offset 15 limit 2 | 154 | 2 | 0 | 2 |
| shard 37 offset 18 limit 2 | 154 | 2 | 0 | 2 |

Existing symbol skipped:

- `000070.SZ`

Backfilled symbols:

- `001256.SZ`
- `002689.SZ`
- `002511.SZ`
- `600258.SH`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Net-new symbols | 4 |
| Planned symbol-periods | 176 |
| Active symbol-periods | 145 |
| Pre-listing skipped symbol-periods | 31 |
| Endpoint requests | 435 |
| Pre-listing skipped endpoint requests | 93 |
| Empty requests | 5 |
| Processed rows | 145 |
| Duplicate rows in quality reports | 0 |
| Required column groups passing | 2 / 2 in both runs |
| Blockers | `[]` |

## Post-Backfill Source Audit

| Metric | Round604 Baseline | Round605 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 154 | 156 |
| Row count | 122,396 | 123,127 |
| Unique symbols | 573 | 577 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round605 completed shard 37 and expanded the local source by four net-new symbols while avoiding a known duplicate, but financial reporting timeliness remains blocked at the source gate. No financial timeliness factor should be preregistered, constructed, or tested from the 577-symbol cache. Continue audited net-new backfill only in small windows, starting shard 38 with a financial-root overlap preview first.
