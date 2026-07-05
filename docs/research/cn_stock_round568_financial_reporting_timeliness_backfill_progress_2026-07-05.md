# CN Stock Round568 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-05

Branch: `codex/data-pipeline-financial-timeliness-round568-20260705`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill after Round567 raised aggregate coverage to 402 unique symbols. This round selected a high net-new shard window, ran one live backfill segment with stock-basic pre-listing filtering, and reran the aggregate source audit. It did not run factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round567 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round568-20260705` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Net-New Selection

Round568 scanned the existing financial statement / financial PIT roots and found shard 25 had 20 / 20 net-new symbols. The committed live segment used the first five:

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 25 offset 0 limit 5 | 116 | 5 | 0 | 5 |

Selected symbols:

- `603071.SH`
- `301345.SZ`
- `002348.SZ`
- `000862.SZ`
- `002033.SZ`

## Backfill Results

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 25 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 3000 --stock-basic-path data\processed\cn_stock_metadata --output-dir data\processed\round568_financial_statement_shard25_offset0_limit5_20260705
```

Result:

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 161 |
| Pre-listing skipped symbol-periods | 59 |
| Endpoint requests | 483 |
| Pre-listing skipped endpoint requests | 177 |
| Empty requests | 4 |
| Processed rows | 161 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

## Post-Backfill Source Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_reporting_timeliness_source_audit.py --financial-root data\processed --output-dir data\reports\round568_financial_reporting_timeliness_aggregate_source_audit_20260705 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --min-unique-symbols 1000 --min-end-years 8
```

Result:

| Metric | Round567 Baseline | Round568 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 116 | 117 |
| Row count | 86,264 | 87,064 |
| Unique symbols | 402 | 407 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Decision

Round568 expanded the local source by another five symbols, but the financial reporting timeliness source remains far below the 1,000-symbol preregistration gate. Continue audited net-new backfill, or rotate to another PIT-safe source if throughput is not worth the provider quota. No financial timeliness factor should be preregistered, constructed, or tested from the 407-symbol cache.
