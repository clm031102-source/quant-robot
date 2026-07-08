# Round690 Next Steps Checklist

Use this after pulling latest `main`. Round690 is expected to be merged back to `main`; do not pull, merge, or revive old Round675 through Round690 data-pipeline topic branches after integration.

## Current Truth

```text
Allowed action: start a dedicated factor_batch candidate-plan branch from merged main.
Latest coverage: 1,002 / 1,000 unique symbols.
Source gate: cleared, blockers [].
Candidate plan allowed: true.
Next direction: financial_reporting_timeliness candidate plan gate.
No portfolio grids, no promotion, no sign/window tuning, no 2026 final-holdout read.
```

The Round630 ten-round review remains the active review record for this run family. Round690 supersedes its source-only blocker by clearing the aggregate source gate, but it does not authorize skipping preregistration, control declaration, or candidate plan gate validation.

## Stop Conditions

- Stop if not on a dedicated `factor_batch` branch before factor-family work.
- Stop if Quant PM startup gate is not `ready` or blockers are not `[]`.
- Stop if `scripts\run_factor_mining_startup_gate.py` does not confirm the repeatable audit-driven next-run protocol.
- Stop if the CN stock data manifest gate fails.
- Stop if a financial reporting timeliness candidate plan gate is not `research_ready`.
- Stop before portfolio grids, promotion, sign/window tuning, mixed-window harvesting, or 2026 final-holdout access.

## Start Commands

```powershell
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/factor-batch-financial-reporting-timeliness-round691-20260708
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-financial-reporting-timeliness-round691-20260708
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-financial-reporting-timeliness-round691-20260708
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Before any IC screen, create a preregistered candidate plan under `configs\` and run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260708.json --output-dir data\reports\round691_financial_reporting_timeliness_candidate_plan_gate_20260708
```

## Candidate Plan Requirements

- Market must be `CN`, asset type `stock`.
- Family should be `financial_reporting_timeliness`.
- Candidate formulas must use only point-in-time statement data with `ann_date` / effective-date lag, never period-end-only availability.
- Candidate plan must declare all default CN stock controls: tradeability, financial PIT timing, source sample integrity, industry/style neutralization, ETF boundary, portfolio construction, strict statistics, China regime coverage, and event contamination controls.
- Candidate plan must keep `portfolio_backtest_allowed=false`, `promotion_allowed=false`, and `final_holdout_available_for_tuning=false`.
- Multiple-testing accounting must count every tested expression and parameter variant.

## Current State

- Round690 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed the source still needed one final small backfill at 997 / 1,000 unique symbols.
- Shard 59 offset 5 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `002550.SZ`, `300124.SZ`, `002056.SZ`, `600199.SH`, `600655.SH`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, 0 empty requests, and 0 duplicate rows in the quality report.
- Aggregate source audit improved coverage to 1,002 unique symbols and 212,387 rows.
- Candidate plan allowed is now true because `source_gate_cleared=true` and blockers are `[]`.

## Explicitly Do Not Do

- Do not continue source-only backfill for this family unless a later source-integrity audit requires it.
- Do not run residual IC before candidate plan gate clearance.
- Do not run portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
