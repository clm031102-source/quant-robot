# Round243 Accounting Quality Shard7 Offset5 And New Substructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand PIT financial-statement coverage by one more five-symbol shard and register the next accounting-quality research substructure without reusing the failed raw/repaired cash-accrual formulas.

**Architecture:** Reuse existing statement backfill, formula smoke, and matrix-label smoke tooling. Do not run the old raw/repaired residual IC prescreen again unless a new candidate implementation exists. Record a seed config for the next orthogonal accounting-quality substructure so the next mining round starts from a hypothesis instead of parameter drift.

**Tech Stack:** Python CLI scripts, Tushare statement ingest, pandas-based PIT statement factor matrix, JSON configs, Markdown reports.

---

### Task 1: Startup And Scope Controls

**Files:**
- Read: `data/reports/round243_factor_mining_startup_gate_20260625/factor_mining_startup_gate.json`
- Read: `data/reports/round243_cn_stock_data_manifest_20260625/cn_stock_data_manifest.json`

- [x] **Step 1: Run startup gate**

Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\round243_factor_mining_startup_gate_20260625
```

Expected: startup gate cleared, CN stock scope, research-only boundary.

- [x] **Step 2: Run CN stock data manifest**

Run:

```powershell
python scripts\run_cn_stock_data_manifest.py --data-root data\processed\office_desktop_20260616_combined_research --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\round243_cn_stock_data_manifest_20260625
```

Expected: blockers empty. Warnings remain evidence boundaries.

### Task 2: Backfill Shard7 Offset5

**Files:**
- Create: `data/processed/round243_financial_statement_shard7_offset5_limit5_20260625/financial_statement_shard_backfill.json`
- Create: `data/reports/round243_accounting_quality_statement_formula_smoke_shard7_offset5_limit5_20260625/accounting_quality_statement_formula_smoke.json`

- [x] **Step 1: Run endpoint-budgeted backfill**

Run:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 7 --symbol-offset 5 --symbol-limit 5 --max-endpoint-requests 660 --output-dir data\processed\round243_financial_statement_shard7_offset5_limit5_20260625
```

Expected: `passes=true`, five symbols, no readiness blockers.

- [x] **Step 2: Run slice-level formula smoke**

Run:

```powershell
python scripts\run_accounting_quality_statement_formula_smoke.py --root data\processed\round243_financial_statement_shard7_offset5_limit5_20260625 --output-dir data\reports\round243_accounting_quality_statement_formula_smoke_shard7_offset5_limit5_20260625
```

Expected: `passes=true`, no duplicate statement keys in the new slice.

### Task 3: Replay Data Readiness Only On 130 Symbols

**Files:**
- Create: `data/reports/round243_accounting_quality_formula_smoke_130_symbol_20260625/accounting_quality_statement_formula_smoke.json`
- Create: `data/reports/round243_accounting_quality_matrix_label_smoke_130_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`

- [x] **Step 1: Build cumulative statement roots**

Include all completed Round236-238 roots, Round241 shard6 offset15, Round242 shard7 offset0, and Round243 shard7 offset5.

- [x] **Step 2: Run cumulative formula smoke**

Expected: unique symbols increase to 130 and PIT formula readiness remains true.

- [x] **Step 3: Run matrix-label smoke**

Expected: alignment violations remain zero. This is data readiness evidence only.

- [x] **Step 4: Confirm old-family IC is intentionally skipped**

Do not run `accounting_quality_statement_residual_ic_shape_prescreen` for the old raw/repaired family in this round.

### Task 4: Register Next Substructure Seed

**Files:**
- Create: `configs/accounting_quality_new_substructure_seed_round243_20260625.json`
- Create: `docs/research/cn_stock_round243_accounting_quality_shard7_offset5_data_prep_and_new_substructure_seed_2026-06-25.md`

- [x] **Step 1: Create seed config**

The seed must include only new accounting-quality substructures:

```json
{
  "family": "accounting_quality_new_substructure",
  "candidate_ideas": [
    "aq_abnormal_accrual_change_reversal",
    "aq_profitability_revision_surprise",
    "aq_post_statement_announcement_drift",
    "aq_balance_sheet_stress_relief",
    "aq_industry_relative_margin_acceleration"
  ]
}
```

- [x] **Step 2: Write report**

Record startup gate, manifest warnings, backfill result, 130-symbol data readiness, and the decision to skip same-family IC replay.

- [x] **Step 3: Verify**

Run JSON validation for new/updated configs, relevant statement smoke/unit tests, result extraction, whitespace check, and Python process check.
