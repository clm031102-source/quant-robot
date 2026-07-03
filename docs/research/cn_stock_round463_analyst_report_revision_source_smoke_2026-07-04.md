# CN Stock Round463 Analyst Report Revision Source Smoke

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profitability-readiness-20260704`

Scope: resume the Round453 analyst report revision direction only as a source-smoke and PIT prescreen. This is research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.

## Project Progress Snapshot

Estimated project completion after this run: 89%.

Evidence already complete:

- `main` was clean and synchronized with `origin/main`.
- Remote topic branch cleanup was complete; remote heads contained only `origin/main`.
- Project audit passed with 2,135 scanned files and no safety hits.
- Quant PM startup gate passed for `office_desktop` / `factor_batch`.
- CN stock factor-mining startup gate cleared on the compliant branch.
- CN stock data manifest had no blockers, but required review because of known data warnings.

Remaining before the project can be called complete:

- Build durable same-day factor-mining evidence from enough PIT history, not just source smoke.
- Find at least one candidate that survives long-cycle IC, neutralization, walk-forward, cost, capacity, regime, and final-holdout rules.
- Keep generated `data/` artifacts local and commit only code, configs, tests, and lightweight summaries.

## Gates Run

Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-profitability-readiness-20260704
```

Result: `ready`, blockers: `[]`.

CN stock startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --config configs\factor_mining_startup_cn_stock.json --output-dir data\reports\factor_mining_startup_gate_20260704_profitability_readiness --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profitability-readiness-20260704 --current-branch codex/factor-batch-cn-stock-profitability-readiness-20260704 --market CN --asset-type stock --confirm-start
```

First attempt was blocked by `branch_prefix_mismatch`; after renaming to `codex/factor-batch-cn-stock-profitability-readiness-20260704`, the gate cleared.

CN stock data manifest:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --data-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\cn_stock_data_manifest_20260704_profitability_readiness --market CN
```

Result: `review_required`, blockers: `[]`.

Warnings:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

These warnings are acceptable for a reviewed source-smoke run, but they must stay recorded and cannot be ignored for promotion.

## Source Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-01-01 --end-date 2024-01-31 --output-dir data\reports\round463_analyst_report_revision_source_smoke_20260704 --processed-output-dir data\processed\round463_analyst_report_revision_source_smoke_20260704 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

Result:

- rows: 1,754
- assets: 780
- fetched windows: 1
- failed windows: 0
- report date range: 2024-01-25 to 2024-01-31
- row-cap warning windows: 0

Follow-up attempt to extend through 2024-02-29 hit the provider limit:

- failed window: 2024-02-01 to 2024-02-29
- error: `report_rc` frequency exceeded, reported as `1 request/hour`

Interpretation: the Round453 blocker changed from "no rows" to "source is usable but slow." This is a meaningful improvement, but it is still not enough history for a profitability claim.

## PIT Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round463_analyst_report_revision_prescreen_source_smoke_20260704 --analysis-start-date 2024-01-01 --analysis-end-date 2024-03-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Result summary:

- candidate count: 4
- factor rows: 2,717
- aligned rows: 5,434
- tests: 8
- research leads: 0
- FDR-significant tests: 0
- neutral-gate pass tests: 0
- promotion allowed candidates: 0
- next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`

Best source-smoke rows:

| Factor | Horizon | Mean IC | ICIR | IC t-stat | Q5-Q1 | Industry neutral IC | Size neutral IC | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `analyst_target_upside_60` | 5 | 0.1750 | 0.929 | 1.86 | 0.0374 | 0.5586 | 0.1092 | no |
| `analyst_eps_revision_90` | 20 | 0.1096 | 1.028 | 2.06 | 0.0258 | 0.4458 | 0.0997 | no |
| `analyst_np_revision_90` | 20 | 0.0989 | 1.098 | 2.20 | 0.0366 | 0.4636 | 0.0868 | no |

Blockers remained:

- not FDR-significant after multiple testing
- size-neutral IC below gate
- year coverage below gate
- later walk-forward, cost, capacity, regime, and final-holdout gates not run

## Decision

Analyst report revision is no longer blocked by an empty source smoke, but it is still not a profitable factor.

Do:

- Cache more `report_rc` monthly windows at the provider-safe pace.
- Rerun the same PIT prescreen after enough months exist for year coverage and multiple-testing evidence.
- Keep this family research-screen only until long-cycle evidence exists.
- Use the updated `run_tushare_analyst_report_cache.py` metadata when the provider blocks a request; rate-limited windows now record `provider_rate_limit`, `retry_after_seconds`, `summary.next_retry_after_seconds`, and `summary.stopped_on_rate_limit` so a scheduler or operator can resume the same failed window without guessing or skipping months.

Do not:

- Tune the four analyst formulas on the one-month source smoke.
- Run a portfolio grid or promotion gate from this partial cache.
- Touch 2026 final holdout for tuning.
