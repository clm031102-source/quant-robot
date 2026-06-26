# Round241 Accounting Quality Shard6 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining five-symbol slice of financial-statement shard6 and rerun accounting-quality gates on the enlarged PIT sample without tuning rejected formulas.

**Architecture:** This round reuses existing statement backfill, formula smoke, matrix-label smoke, and residual IC prescreen commands. It is a data-power expansion and gate replay, not a new parameter search or portfolio conversion.

**Tech Stack:** Python CLI scripts, Tushare statement ingest, JSON/Markdown reports, pandas-based IC prescreen.

---

### Task 1: Execute Final Shard6 Slice

**Files:**
- Read: `data/reports/round236_financial_statement_symbol_shard_plan_20260625/financial_statement_symbol_shard_plan.json`
- Create: `data/processed/round241_financial_statement_shard6_offset15_limit5_20260625/financial_statement_shard_backfill.json`
- Create: `data/processed/round241_financial_statement_shard6_offset15_limit5_20260625/financial_statement_shard_backfill.md`

- [x] **Step 1: Confirm the target slice**

Run:

```powershell
$p='data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json'
$j=Get-Content -Raw $p | ConvertFrom-Json
$s=$j.shards | Where-Object { $_.shard_id -eq 6 }
$s.symbols[15..19]
```

Expected: five symbols: `300106.SZ`, `000681.SZ`, `000927.SZ`, `000421.SZ`, `601601.SH`.

- [x] **Step 2: Run endpoint-budgeted backfill**

Run:

```powershell
python scripts\run_financial_statement_shard_backfill.py `
  --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json `
  --shard-id 6 `
  --symbol-offset 15 `
  --symbol-limit 5 `
  --max-endpoint-requests 660 `
  --output-dir data\processed\round241_financial_statement_shard6_offset15_limit5_20260625
```

Expected: `passes=true`, `symbol_count=5`, `period_count=44`, `endpoint_request_count=660`, and no readiness blockers.

### Task 2: Replay Accounting-Quality Gates On Expanded Sample

**Files:**
- Create: `data/reports/round241_accounting_quality_formula_smoke_120_symbol_20260625/accounting_quality_statement_formula_smoke.json`
- Create: `data/reports/round241_accounting_quality_matrix_label_smoke_120_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`
- Create: `data/reports/round241_accounting_quality_raw_prescreen_120_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Create: `data/reports/round241_accounting_quality_repaired_prescreen_120_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`

- [x] **Step 1: Build the statement root list**

Use all existing Round236-238 roots plus the new Round241 root. The expected unique symbol count after deduplication is 120.

- [x] **Step 2: Run formula smoke**

Run `scripts\run_accounting_quality_statement_formula_smoke.py` with the full statement root list and output to `data\reports\round241_accounting_quality_formula_smoke_120_symbol_20260625`.

Expected: `passes=true`, no duplicate-key blocker after deduplication, and all required formula coverage rows present.

- [x] **Step 3: Run matrix-label smoke**

Run `scripts\run_accounting_quality_statement_matrix_label_smoke.py` with the same root list.

Expected: `passes=true`, first-tradable-date-after-ann-date alignment, and zero alignment violations.

- [x] **Step 4: Run raw and repaired residual IC prescreens**

Run `scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py` twice: once with `--factor-mode raw`, once with `--factor-mode repaired`.

Expected: report the number of candidates, tests, FDR-significant rows, neutral-gate rows, research leads, and promotion-allowed rows. Do not run a portfolio grid unless the gate creates a true research lead.

### Task 3: Document The Round

**Files:**
- Create: `docs/research/cn_stock_round241_accounting_quality_shard6_completion_and_120_symbol_replay_2026-06-25.md`
- Modify if needed: `configs/accounting_quality_statement_backfill_round236_20260625.json`
- Modify if needed: `configs/accounting_quality_statement_smoke_plan_round237_20260625.json`

- [x] **Step 1: Write the round report**

The report must include the new backfill summary, formula/matrix smoke status, raw and repaired IC summaries, best rows, and the decision.

- [x] **Step 2: Enforce stop-loss discipline**

If raw and repaired prescreens still produce zero research leads, mark the three repaired formulas as not worth tuning and prefer either more sample expansion or a genuinely different accounting-quality substructure.

- [x] **Step 3: Verify**

Run:

```powershell
python -m json.tool configs\accounting_quality_statement_smoke_plan_round237_20260625.json > $null
python -m json.tool configs\accounting_quality_statement_backfill_round236_20260625.json > $null
python -m unittest tests.unit.test_financial_statement_shard_backfill_cli tests.unit.test_accounting_quality_statement_formula_smoke_cli tests.unit.test_accounting_quality_statement_matrix_label_smoke_cli tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

Expected: JSON validation succeeds and all selected tests pass.
