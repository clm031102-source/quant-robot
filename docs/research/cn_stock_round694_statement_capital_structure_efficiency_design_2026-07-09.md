# CN Stock Round694 Statement Capital Structure Efficiency Design

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-rotation-round694-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Startup Evidence

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Direction

Round694 rotates away from local Round691 financial reporting timeliness, local Round692 PEAD gap-reversal source repair, and local Round693 statement working-capital pressure, none of which produced a promotable candidate.

The new family is `statement_capital_structure_efficiency`. It uses PIT financial statement fields that are not part of the existing accounting-quality formula set: book-equity buffer, liability-to-equity leverage, operating cashflow relative to equity, and revenue generated per unit of liabilities.

This family is not a direct profitability-quality rerun. It does not test ROE, ROA, net-profit margin, gross margin, net-profit growth, or old `fina_indicator` profitability-quality candidates. It also avoids Round693 inventory/receivable/payable/cash-current-liability working-capital pressure transforms.

## Source Snapshot

- Local statement root: `data/processed`
- Statement rows in coverage check: 40,665
- Statement assets in coverage check: 959
- `total_assets`: 40,275 rows, 959 assets, 99.04% coverage
- `total_liab`: 40,274 rows, 959 assets, 99.04% coverage
- `total_hldr_eqy_exc_min_int`: 40,274 rows, 959 assets, 99.04% coverage
- `n_cashflow_act`: 40,339 rows, 959 assets, 99.20% coverage
- `free_cashflow`: 39,456 rows, 959 assets, 97.03% coverage
- `total_revenue`: 40,351 rows, 959 assets, 99.23% coverage
- Signal dating rule: first trading date strictly after `ann_date`
- Final holdout available for tuning: false

## Pre-Registered Candidates

- `scs_equity_buffer_improvement`
- `scs_liability_to_equity_deleveraging`
- `scs_operating_cashflow_equity_buffer`
- `scs_revenue_to_liability_efficiency`
- `scs_balanced_capital_structure_efficiency`

## Candidate-Plan Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round694_statement_capital_structure_efficiency_20260709.json --gate-stage discovery --output-dir data\reports\round694_statement_capital_structure_efficiency_candidate_plan_gate_20260709
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

## Blocked Actions

- No portfolio grid.
- No promotion gate.
- No sign flip.
- No formula, lag, horizon, or window tuning.
- No mixed-window harvesting.
- No direct profitability-quality, working-capital pressure, financial-reporting-timeliness, PEAD, daily-basic, public technical, northbound, or margin-credit family reuse.
- No live trading, broker read, account read, or order placement.
- No 2026 final-holdout read for tuning.

Generated `data/reports` evidence remains local and uncommitted.
