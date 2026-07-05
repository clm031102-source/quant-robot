# CN Stock Round567 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round567-20260705`

Scope: dedicated data-pipeline work to expand the local financial reporting timeliness / PIT statement source after Round566 found the cache too narrow for factor preregistration. This round used overlap previews, then live shard backfills for net-new symbols only. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round566 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round567-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Overlap Previews

Round567 first previewed shard 19 windows without provider calls:

| Preview | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: |
| shard 19 offset 0 limit 6 | 6 | 2 | 4 |
| shard 19 offset 6 limit 6 | 6 | 2 | 4 |

The live run split around existing symbols so provider calls were spent on net-new symbols only:

- offset 0 limit 3: `002461.SZ`, `600658.SH`, `002014.SZ`
- offset 4 limit 1: `002571.SZ`
- offset 6 limit 3: `000762.SZ`, `000811.SZ`, `000917.SZ`
- offset 11 limit 1: `000668.SZ`

## Backfill Results

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Passes | Blockers |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| offset 0 limit 3 | 3 | 396 | 132 | 3 | true | `[]` |
| offset 4 limit 1 | 1 | 132 | 44 | 0 | true | `[]` |
| offset 6 limit 3 | 3 | 396 | 132 | 2 | true | `[]` |
| offset 11 limit 1 | 1 | 132 | 44 | 0 | true | `[]` |
| Total | 8 | 1,056 | 352 | 5 | true | `[]` |

All four segment reports passed their required column-group, quality, and readiness checks. Generated provider data stayed under `data/processed` and generated audit reports stayed under `data/reports`; neither path is Git-tracked.

## Post-Backfill Source Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_reporting_timeliness_source_audit.py --financial-root data\processed --output-dir data\reports\round567_financial_reporting_timeliness_aggregate_source_audit_20260705 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --min-unique-symbols 1000 --min-end-years 8
```

Result:

| Metric | Round566 Baseline | Round567 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 112 | 116 |
| Row count | 84,499 | 86,264 |
| Unique symbols | 394 | 402 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round567 made real data-pipeline progress, but financial reporting timeliness remains blocked at the source gate. Do not preregister, construct, or test financial timeliness factors from the 402-symbol cache. The next useful work is more net-new backfill, preferably in audited shard windows with overlap previews, until the source can clear the 1,000-symbol minimum.
