# CN Stock Round566 Financial Reporting Timeliness Source Audit

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round566-new-pit-source-20260705`

Scope: after Round565 rejected HK-hold sponsorship, Round566 checked whether the local financial reporting timeliness / PIT statement source has become broad enough to support candidate preregistration. This was a local aggregate source audit only. It did not run provider downloads, factor generation, IC screens, portfolio grids, promotion gates, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, with Round565 merged and topic branch deleted |
| New branch | `codex/factor-batch-cn-stock-round566-new-pit-source-20260705` |
| Startup context | `office_desktop` / `factor_batch`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| CN stock startup gate | `cleared`, blockers `[]` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Data manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |

## Source Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_reporting_timeliness_source_audit.py --financial-root data\processed --output-dir data\reports\round566_financial_reporting_timeliness_aggregate_source_audit_20260705 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --min-unique-symbols 1000 --min-end-years 8
```

Result:

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 112 |
| Row count | 84,499 |
| Unique symbols | 394 |
| Minimum required symbols | 1,000 |
| Minimum required end years | 8 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

## Decision

Financial reporting timeliness remains blocked at the source gate. Do not preregister factors, run residual IC, tune formulas, or portfolio-test this source from the current 394-symbol local cache. The next useful work is either a dedicated data-pipeline branch to continue the Round303-style backfill with overlap preview and stock-basic pre-listing filtering, or rotation to another accessible PIT-safe source.
