# Round242 Accounting Quality Shard7 Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first five-symbol slice of financial-statement shard7 and replay accounting-quality gates on the enlarged PIT sample.

**Architecture:** Reuse the existing financial-statement shard backfill, formula smoke, matrix-label smoke, and residual IC prescreen commands. This round expands sample power and rejects promotion unless statistical and neutralization gates produce a true research lead.

**Tech Stack:** Python CLI scripts, Tushare statement ingest, pandas-based accounting-quality factor matrix, JSON and Markdown reports.

---

### Task 1: Confirm Startup And Target Slice

**Files:**
- Read: `configs/factor_mining_startup_cn_stock.json`
- Read: `data/reports/round236_financial_statement_symbol_shard_plan_20260625/financial_statement_symbol_shard_plan.json`
- Create: `data/reports/round242_factor_mining_startup_gate_20260625/factor_mining_startup_gate.json`
- Create: `data/reports/round242_cn_stock_data_manifest_20260625/cn_stock_data_manifest.json`

- [x] **Step 1: Run startup gate**

Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\round242_factor_mining_startup_gate_20260625
```

Expected: startup gate cleared, CN stock scope, no live boundary.

- [x] **Step 2: Run CN stock data manifest**

Run:

```powershell
python scripts\run_cn_stock_data_manifest.py --data-root data\processed\office_desktop_20260616_combined_research --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\round242_cn_stock_data_manifest_20260625
```

Expected: no blockers. Warnings are recorded as evidence boundaries.

- [x] **Step 3: Confirm shard7 offset0 symbols**

Expected symbols: `000509.SZ`, `000014.SZ`, `600611.SH`, `603569.SH`, `000056.SZ`.

### Task 2: Execute Shard7 Offset0 Backfill

**Files:**
- Create: `data/processed/round242_financial_statement_shard7_offset0_limit5_20260625/financial_statement_shard_backfill.json`
- Create: `data/reports/round242_accounting_quality_statement_formula_smoke_shard7_offset0_limit5_20260625/accounting_quality_statement_formula_smoke.json`

- [x] **Step 1: Run endpoint-budgeted backfill**

Run:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 7 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 660 --output-dir data\processed\round242_financial_statement_shard7_offset0_limit5_20260625
```

Expected: `passes=true`, `symbol_count=5`, `endpoint_request_count=660`, no readiness blockers.

- [x] **Step 2: Run slice-level formula smoke**

Run:

```powershell
python scripts\run_accounting_quality_statement_formula_smoke.py --root data\processed\round242_financial_statement_shard7_offset0_limit5_20260625 --output-dir data\reports\round242_accounting_quality_statement_formula_smoke_shard7_offset0_limit5_20260625
```

Expected: `passes=true`, 5 formulas with values.

### Task 3: Replay 125-Symbol Gates

**Files:**
- Create: `data/reports/round242_accounting_quality_formula_smoke_125_symbol_20260625/accounting_quality_statement_formula_smoke.json`
- Create: `data/reports/round242_accounting_quality_matrix_label_smoke_125_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`
- Create: `data/reports/round242_accounting_quality_raw_prescreen_125_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Create: `data/reports/round242_accounting_quality_repaired_prescreen_125_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`

- [x] **Step 1: Build statement roots**

Use all completed Round236-238 roots, Round241 shard6 offset15, and Round242 shard7 offset0.

- [x] **Step 2: Run cumulative formula smoke**

Expected: unique symbols increase to 125.

- [x] **Step 3: Run matrix-label smoke**

Expected: zero alignment violations.

- [x] **Step 4: Run raw and repaired residual IC prescreens**

Expected: record candidate counts, FDR significant rows, neutral-gate passes, research leads, and promotion-allowed counts. Do not run portfolio grids unless a true lead appears.

### Task 4: Report And Verify

**Files:**
- Create: `docs/research/cn_stock_round242_accounting_quality_shard7_expansion_and_125_symbol_replay_2026-06-25.md`
- Modify: `configs/accounting_quality_statement_backfill_round236_20260625.json`
- Modify: `configs/accounting_quality_statement_smoke_plan_round237_20260625.json`

- [x] **Step 1: Write report**

Summarize startup gate, manifest warnings, backfill, formula/matrix gate status, raw/repaired IC results, and decision.

- [x] **Step 2: Update configs**

Record latest Round242 report paths and next segment.

- [x] **Step 3: Verify**

Run JSON validation, relevant unit tests, result consistency extraction, and whitespace check.
