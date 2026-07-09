# Round693 Statement Working Capital Pressure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-register and screen five PIT statement working-capital pressure candidates for CN stock alpha research.

**Architecture:** Reuse the existing accounting-quality statement formula, matrix-label, and residual prescreen pipeline. Add a narrow `statement_working_capital_pressure` mode that computes new formulas from statement columns and filters to exactly the five Round693 candidates.

**Tech Stack:** Python, pandas, pytest, existing CN stock factor-mining gates and `data/processed` local statement cache.

---

### Task 1: Candidate Plan Gate

**Files:**
- Create: `configs/factor_mining_candidate_plan_round693_statement_working_capital_pressure_20260709.json`
- Create: `docs/research/cn_stock_round693_statement_working_capital_pressure_candidate_plan_gate_2026-07-09.md`

- [ ] **Step 1: Write the pre-registration config**

Define the `statement_working_capital_pressure` family with five candidates:

```text
swcp_cash_current_liability_improvement
swcp_operating_working_capital_release
swcp_inventory_receivable_efficiency_improvement
swcp_free_cashflow_liability_buffer
swcp_balanced_cash_working_capital_pressure
```

- [ ] **Step 2: Run the candidate plan gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round693_statement_working_capital_pressure_20260709.json --output-dir data\reports\round693_statement_working_capital_pressure_candidate_plan_gate_20260709
```

Expected: `status` is `research_ready`, `candidate_plan_gate_cleared` is true, and `blockers` is empty.

- [ ] **Step 3: Record the lightweight gate summary**

Write the report path, gate status, candidate names, data-manifest warnings, and blocked actions to the research doc. Do not copy large `data/reports` payloads into Git.

- [ ] **Step 4: Commit the gate artifacts**

Run:

```powershell
git add configs/factor_mining_candidate_plan_round693_statement_working_capital_pressure_20260709.json docs/research/cn_stock_round693_statement_working_capital_pressure_candidate_plan_gate_2026-07-09.md docs/superpowers/specs/2026-07-09-round693-statement-working-capital-pressure-design.md docs/superpowers/plans/2026-07-09-round693-statement-working-capital-pressure.md
git commit -m "Register Round693 statement working capital pressure"
```

### Task 2: Formula And Mode Implementation

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_formula_smoke.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Add failing formula tests**

Add assertions that the formula smoke can calculate:

```text
swcp_cash_current_liability_improvement
swcp_operating_working_capital_release
swcp_inventory_receivable_efficiency_improvement
swcp_free_cashflow_liability_buffer
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_formula_smoke.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py -q
```

Expected first failure: missing Round693 `swcp_*` formula names or unsupported `factor_mode`.

- [ ] **Step 3: Implement formulas**

Add fixed formulas:

```text
delta_4q(c_cash_equ_end_period / total_cur_liab)
-delta_4q((inventories + accounts_receiv - accounts_pay) / total_assets)
-delta_4q((inventories + accounts_receiv) / total_revenue)
free_cashflow / total_liab + c_cash_equ_end_period / total_cur_liab
```

Use `revenue` only as a fallback when `total_revenue` is unavailable.

- [ ] **Step 4: Add residual prescreen mode**

Add `factor_mode="statement_working_capital_pressure"` and candidate specs for the five Round693 names. Build the balanced factor as a frozen equal-weight cross-sectional percentile-rank composite.

- [ ] **Step 5: Run focused tests and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_formula_smoke.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py -q
git add src/quant_robot/ops/accounting_quality_statement_formula_smoke.py src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py tests/unit/test_accounting_quality_statement_formula_smoke.py tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py
git commit -m "Add Round693 statement working capital pressure mode"
```

### Task 3: Matrix Smoke And Residual Prescreen

**Files:**
- Create: `docs/research/cn_stock_round693_statement_working_capital_pressure_prescreen_2026-07-09.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Run formula smoke**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_formula_smoke.py --statement-root data\processed --output-dir data\reports\round693_statement_working_capital_pressure_formula_smoke_20260709
```

Expected: pass with nonzero `swcp_*` formula coverage.

- [ ] **Step 2: Run matrix-label smoke**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_matrix_label_smoke.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round693_statement_working_capital_pressure_matrix_label_smoke_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.60
```

Expected: pass, zero alignment violations, no final-holdout rows.

- [ ] **Step 3: Run residual prescreen**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --factor-mode statement_working_capital_pressure --output-dir data\reports\round693_statement_working_capital_pressure_residual_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 8 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.35
```

Expected: result records five candidates, all tests counted, and either research leads or an explicit zero-lead rejection.

- [ ] **Step 4: Record and commit the conclusion**

Write a concise research report and index entry. Commit only code, tests, configs, and lightweight docs; keep `data/reports` local and ignored.
