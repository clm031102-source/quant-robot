# Round244 Accounting Quality New Substructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first Round244 accounting-quality substructure formulas so the next IC screen no longer reruns the failed raw/repaired cash-accrual family.

**Architecture:** Extend the existing statement formula registry and formula calculation path used by formula smoke, matrix-label smoke, and residual IC prescreen. Start with two field-covered hypotheses from the Round243 seed: abnormal accrual change and balance-sheet stress relief. Keep the implementation PIT-safe by using only same-row report values and trailing same-asset shifts.

**Tech Stack:** Python, pandas, existing `accounting_quality_statement_formula_smoke`, matrix-label smoke, unit tests, JSON configs, Markdown reports.

---

### Task 1: Red Tests For New Formula Registry

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_formula_smoke.py`
- Modify: `tests/unit/test_accounting_quality_statement_matrix_label_smoke.py`

- [x] **Step 1: Add formula smoke assertions**

Add assertions that `aq_abnormal_accrual_change_reversal` and `aq_balance_sheet_stress_relief` appear in formula coverage with positive valid rows.

- [x] **Step 2: Add matrix-label assertions**

Add assertions that the factor matrix and candidate summaries include the two new factor names and keep PIT signal-date alignment.

- [x] **Step 3: Run targeted tests and verify red**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_formula_smoke tests.unit.test_accounting_quality_statement_matrix_label_smoke
```

Expected: tests fail because the new factors are not yet registered.

### Task 2: Implement Minimal New Formula Support

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`

- [x] **Step 1: Register new formula specs**

Add two `FORMULA_SPECS` entries:

- `aq_abnormal_accrual_change_reversal`
- `aq_balance_sheet_stress_relief`

- [x] **Step 2: Compute PIT-safe values**

For abnormal accrual change, compute the negative change in accrual pressure versus its own trailing four-quarter value. For stress relief, compute falling liability stress confirmed by cash conversion, using only current and trailing same-asset values.

- [x] **Step 3: Run targeted tests and verify green**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_formula_smoke tests.unit.test_accounting_quality_statement_matrix_label_smoke
```

Expected: tests pass.

### Task 3: Run Round244 Data Gates And Initial Prescreen

**Files:**
- Create: `data/reports/round244_accounting_quality_new_substructure_formula_smoke_130_symbol_20260625/accounting_quality_statement_formula_smoke.json`
- Create: `data/reports/round244_accounting_quality_new_substructure_matrix_label_smoke_130_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`
- Create: `data/reports/round244_accounting_quality_new_substructure_residual_ic_prescreen_130_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Create: `docs/research/cn_stock_round244_accounting_quality_new_substructure_implementation_and_prescreen_2026-06-25.md`

- [x] **Step 1: Run 130-symbol formula smoke**

Use the same completed statement roots from Round243 and verify the new formula count increases.

- [x] **Step 2: Run 130-symbol matrix-label smoke**

Verify zero alignment violations and new candidate summaries.

- [x] **Step 3: Run residual IC shape prescreen in raw mode**

This was executed with `factor_mode=new_substructure` so old raw cash-accrual formulas were not mixed into the Round244 conclusion. Interpret any output as IC-shape evidence only.

- [x] **Step 4: Write Round244 report**

Record candidate count, label alignment, IC/FDR/neutral results, and whether any new factor deserves walk-forward review.

### Task 4: Verification And Guardrails

**Files:**
- Modify: `docs/superpowers/plans/2026-06-25-round244-accounting-quality-new-substructure-implementation.md`

- [x] **Step 1: Run JSON/config checks**

Validate any new or updated JSON configs.

- [x] **Step 2: Run unit tests**

Run accounting-quality formula, matrix-label, and residual IC tests.

- [x] **Step 3: Check whitespace and Python processes**

Run trailing whitespace search on edited files and confirm no leftover Python workers.
