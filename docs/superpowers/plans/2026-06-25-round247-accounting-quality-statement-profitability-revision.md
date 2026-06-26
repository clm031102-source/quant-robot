# Round247 Accounting Quality Statement Profitability Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and test a narrow Round247 statement profitability revision factor family, then run a long-cycle CN-stock residual IC prescreen.

**Architecture:** Reuse the existing accounting-quality statement formula and residual IC prescreen pipeline. Add two realized-statement profitability acceleration formulas, expose a new `statement_profitability_revision` factor mode, and keep this stage as PIT residual IC evidence only.

**Tech Stack:** Python, pandas, unittest, existing Tushare statement/bars/daily-basic processed data, existing `accounting_quality_statement_*` ops and CLI.

---

### Task 1: Red Tests For Formula And Prescreen Mode

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_formula_smoke.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py`

- [ ] **Step 1: Add formula coverage expectations**

```python
coverage = {row["factor_name"]: row for row in result["formula_coverage"]}
self.assertEqual(coverage["aq_profitability_revision_cash_confirmed"]["valid_rows"], 2)
self.assertEqual(coverage["aq_profitability_revision_asset_disciplined"]["valid_rows"], 2)
```

- [ ] **Step 2: Add prescreen mode expectation**

```python
result = build_accounting_quality_statement_residual_ic_shape_prescreen(
    statement_roots=[statement_root],
    bars_roots=[bars_root],
    stock_basic_path=stock_basic_root,
    daily_basic_roots=[daily_basic_root],
    horizons=(5,),
    factor_mode="statement_profitability_revision",
    min_cross_section=4,
    min_ic_observations=2,
    min_neutral_ic_t_stat=0.0,
)
self.assertEqual(result["factor_mode"], "statement_profitability_revision")
self.assertEqual(result["summary"]["candidate_count"], 2)
self.assertEqual(
    result["source_context"]["candidate_family"],
    "accounting_quality_statement_profitability_revision",
)
self.assertEqual(
    {row["factor_name"] for row in result["results"]},
    {
        "aq_profitability_revision_cash_confirmed",
        "aq_profitability_revision_asset_disciplined",
    },
)
```

- [ ] **Step 3: Add CLI mode expectation**

```python
result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
    statement_roots=[statement_root],
    bars_roots=[bars_root],
    stock_basic_path=stock_basic_root,
    daily_basic_roots=[daily_basic_root],
    output_dir=output_dir,
    horizons=(5,),
    factor_mode="statement_profitability_revision",
    min_cross_section=4,
    min_ic_observations=2,
    min_neutral_ic_t_stat=0.0,
)
self.assertEqual(result["factor_mode"], "statement_profitability_revision")
self.assertEqual(result["summary"]["candidate_count"], 2)
```

- [ ] **Step 4: Run red tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest tests.unit.test_accounting_quality_statement_formula_smoke tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

Expected: fail because the two new formulas and `statement_profitability_revision` factor mode do not exist yet.

### Task 2: Implement Statement Profitability Revision Family

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Add two formula specs**

```python
{
    "factor_name": "aq_profitability_revision_cash_confirmed",
    "formula": "delta_4q(netprofit / total_assets) + delta_4q(n_cashflow_act / total_assets)",
    "economic_direction": "profitability_acceleration_confirmed_by_operating_cashflow_better",
    "required_columns": ["asset_id", "netprofit", "n_cashflow_act", "total_assets"],
},
{
    "factor_name": "aq_profitability_revision_asset_disciplined",
    "formula": "delta_4q(netprofit / total_assets) - abs(pct_change_4q(total_assets))",
    "economic_direction": "profitability_acceleration_without_balance_sheet_expansion_better",
    "required_columns": ["asset_id", "netprofit", "total_assets"],
},
```

- [ ] **Step 2: Compute formula values**

```python
denominator = output["total_assets"].replace(0, np.nan)
roa = output["netprofit"] / denominator
cash_roa = output["n_cashflow_act"] / denominator
roa_revision = roa - roa.groupby(output["asset_id"]).shift(4)
cash_roa_revision = cash_roa - cash_roa.groupby(output["asset_id"]).shift(4)
asset_growth_abs = output.groupby("asset_id")["total_assets"].pct_change(4, fill_method=None).abs()
output["aq_profitability_revision_cash_confirmed"] = roa_revision + cash_roa_revision
output["aq_profitability_revision_asset_disciplined"] = roa_revision - asset_growth_abs
```

- [ ] **Step 3: Wire the new factor mode**

Add `STATEMENT_PROFITABILITY_REVISION_FACTOR_NAMES`, candidate specs, valid factor mode, CLI choice, source context, and next directions:

```python
NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITH_LEADS = "round248_accounting_quality_statement_profitability_revision_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITHOUT_LEADS = "round248_rotate_to_external_revision_or_nonfinancial_event_context"
```

- [ ] **Step 4: Run green tests**

Run the same unittest command. Expected: pass.

### Task 3: Long-Cycle Prescreen And Research Artifacts

**Files:**
- Create: `configs/accounting_quality_statement_profitability_revision_round247_20260625.json`
- Create: `docs/research/cn_stock_round247_accounting_quality_statement_profitability_revision_2026-06-25.md`
- Create: `docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md`

- [ ] **Step 1: Run 130-symbol long-cycle prescreen**

Run:

```powershell
.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed\round236_financial_statement_shard1_full100_20260625 --statement-root data\processed\round241_financial_statement_shard6_20260625 --statement-root data\processed\round242_financial_statement_shard7_offset0_20260625 --statement-root data\processed\round243_financial_statement_shard7_offset5_20260625 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --daily-basic-root data\processed\cn_stock_long_history_2015_202306 --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\round247_accounting_quality_statement_profitability_revision_residual_ic_130_symbol_20260625 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --factor-mode statement_profitability_revision --allow-not-ready
```

- [ ] **Step 2: Summarize empirical result**

Extract candidate count, factor rows, aligned rows, IC, ICIR, t-stat, FDR flag, neutral ICs, research-lead count, and next direction from:

```text
data/reports/round247_accounting_quality_statement_profitability_revision_residual_ic_130_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json
```

- [ ] **Step 3: Write config and reports**

Document the exact hypothesis, data roots, PIT policy, result metrics, decision, and next direction. The three-round review must cover Round245 directional audit, Round246 event drift, and Round247 profitability revision.

### Task 4: Verification

**Files:**
- Verify changed Python, JSON, and Markdown files only.

- [ ] **Step 1: Parse new JSON config**

```powershell
.venv\Scripts\python.exe -m json.tool configs\accounting_quality_statement_profitability_revision_round247_20260625.json
```

- [ ] **Step 2: Run focused regression tests**

```powershell
.venv\Scripts\python.exe -m unittest tests.unit.test_accounting_quality_statement_formula_smoke tests.unit.test_accounting_quality_statement_formula_smoke_cli tests.unit.test_accounting_quality_statement_matrix_label_smoke tests.unit.test_accounting_quality_statement_matrix_label_smoke_cli tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

- [ ] **Step 3: Check whitespace on touched files**

```powershell
.venv\Scripts\python.exe - <<'PY'
from pathlib import Path
paths = [
    Path("src/quant_robot/ops/accounting_quality_statement_formula_smoke.py"),
    Path("src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py"),
    Path("scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py"),
    Path("tests/unit/test_accounting_quality_statement_formula_smoke.py"),
    Path("tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py"),
    Path("tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py"),
    Path("configs/accounting_quality_statement_profitability_revision_round247_20260625.json"),
    Path("docs/research/cn_stock_round247_accounting_quality_statement_profitability_revision_2026-06-25.md"),
    Path("docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md"),
]
bad = []
for path in paths:
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.rstrip() != line:
            bad.append((str(path), idx))
if bad:
    raise SystemExit(bad)
print("trailing whitespace check passed")
PY
```

- [ ] **Step 4: Confirm no Python worker is left running**

```powershell
Get-Process python -ErrorAction SilentlyContinue
```

Expected: no long-running factor worker left by this round unless explicitly continuing into the next round.
