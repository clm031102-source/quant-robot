# CN Stock Round693 Statement Working Capital Pressure Candidate Plan Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-statement-working-capital-pressure-round693-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Startup Gates

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Direction

Round693 rotates away from failed Round691 financial reporting timeliness and failed Round692 PEAD gap-reversal source repair. The new family is `statement_working_capital_pressure`.

The family tests whether improving cash coverage, falling operating working-capital lockup, and stronger free-cashflow liability buffers predict later cross-sectional returns after financial statement release. It is explicitly not a same-family rerun of realized profitability revision, cash-conversion event drift, reporting timeliness, or PEAD gap reversal.

## Source Snapshot

- Local statement root: `data/processed`
- Statement rows in the column-coverage check: 40,665
- Statement assets in the column-coverage check: 959
- High-coverage new fields: `c_cash_equ_end_period`, `total_cur_liab`, `inventories`, `accounts_receiv`, `accounts_pay`, `total_revenue`, `free_cashflow`, `total_liab`
- Signal dating rule: first trading date strictly after `ann_date`
- Final holdout available for tuning: false

## Candidate Plan Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round693_statement_working_capital_pressure_20260709.json --output-dir data\reports\round693_statement_working_capital_pressure_candidate_plan_gate_20260709
```

Result:

- Status: `research_ready`
- Candidate plan cleared: true
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false
- Blockers: `[]`
- Candidates: 5
- Active candidates: 5
- Unique candidate names: 5
- Complete control areas: 9 / 9

## Pre-Registered Candidates

- `swcp_cash_current_liability_improvement`
- `swcp_operating_working_capital_release`
- `swcp_inventory_receivable_efficiency_improvement`
- `swcp_free_cashflow_liability_buffer`
- `swcp_balanced_cash_working_capital_pressure`

## Allowed Next Action

Run formula coverage smoke, matrix-label smoke, and residual IC shape prescreen for exactly these five candidates with fixed 5D and 20D horizons. Carry forward data-manifest warnings into the prescreen report.

## Blocked Actions

- No portfolio grid.
- No promotion gate.
- No sign flip.
- No formula, lag, horizon, or window tuning.
- No mixed-window harvesting.
- No live trading, broker read, account read, or order placement.
- No 2026 final-holdout read for tuning.

Generated `data/reports` evidence remains local and uncommitted.
