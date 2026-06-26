# Round245 Accounting Quality Directional Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a preregistered sign-direction audit for the one Round244 abnormal-accrual clue without pretending the sign flip is a free discovery.

**Architecture:** Add a dedicated residual IC `factor_mode=new_substructure_directional_audit` that creates one audit-only factor by negating `aq_abnormal_accrual_change_reversal` and renaming it. Keep old raw/repaired factors and the two Round244 new-substructure factors out of this audit result. The audit can only produce IC-shape evidence; promotion and portfolio conversion stay blocked.

**Tech Stack:** Python, pandas, existing accounting-quality residual IC prescreen, unittest, JSON configs, Markdown reports.

---

### Task 1: Red Tests For Directional Audit Mode

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py`

- [x] **Step 1: Add helper test**

Add a test that calls `build_accounting_quality_statement_directional_audit_factor_frame` and expects only `aq_abnormal_accrual_change_reversal_sign_flip_audit` with the source factor value negated.

- [x] **Step 2: Add build-mode test**

Add a test that `factor_mode="new_substructure_directional_audit"` produces one candidate and marks the source context as `accounting_quality_new_substructure_directional_audit`.

- [x] **Step 3: Add CLI mode test**

Add a CLI test that passes `factor_mode="new_substructure_directional_audit"` and writes the normal residual IC outputs.

- [x] **Step 4: Run red tests**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

Expected: fail because the helper and mode do not exist yet.

### Task 2: Implement Directional Audit Mode

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [x] **Step 1: Add constants and helper**

Add source/audit factor constants and implement `build_accounting_quality_statement_directional_audit_factor_frame`.

- [x] **Step 2: Add candidate spec and build branch**

Support `factor_mode="new_substructure_directional_audit"` with one candidate and dedicated next-direction strings.

- [x] **Step 3: Add CLI choice**

Allow `--factor-mode new_substructure_directional_audit`.

- [x] **Step 4: Run green tests**

Run the same targeted tests and confirm they pass.

### Task 3: Run Round245 Prescreen And Report

**Files:**
- Create: `data/reports/round245_accounting_quality_directional_audit_residual_ic_130_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Create: `configs/accounting_quality_directional_audit_round245_20260625.json`
- Create: `docs/research/cn_stock_round245_accounting_quality_directional_audit_2026-06-25.md`

- [x] **Step 1: Run 130-symbol directional audit**

Use the Round243 130-symbol statement roots and the existing long-cycle bar/daily-basic roots.

- [x] **Step 2: Extract audit metrics**

Record IC, ICIR, t-stat, p-value, FDR, neutral gates, and research lead status.

- [x] **Step 3: Write config and report**

State whether the sign flip is rejected, a research lead, or still only a weak clue.

### Task 4: Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-06-25-round245-accounting-quality-directional-audit.md`

- [x] **Step 1: Run JSON checks**

Validate Round245 JSON config and touched configs.

- [x] **Step 2: Run unit tests**

Run formula, matrix-label, residual IC, and CLI tests relevant to accounting quality.

- [x] **Step 3: Check whitespace and Python processes**

Run trailing whitespace search on edited files and verify no Python worker remains.
