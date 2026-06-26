# Accounting Quality Repaired Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small repaired accounting-quality candidate layer after the 115-symbol raw formula residual IC failure.

**Architecture:** Keep the existing PIT statement factor and residual IC prescreen intact. Add repaired candidates in `accounting_quality_statement_residual_ic_shape_prescreen.py` by transforming the already PIT-safe raw factor frame into industry-relative and size/liquidity residual composites, then reuse the same IC/FDR/neutralization summary and no-promotion policy.

**Tech Stack:** Python, pandas, existing `DatasetStore`, existing profitability-event neutral IC summarizer, unittest.

---

### Task 1: Repaired Factor Frame Behavior

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Write the failing test**

Add a test that imports `build_accounting_quality_statement_repaired_factor_frame`, builds one date with two industries and correlated size/liquidity exposures, and asserts the repaired frame contains exactly these non-raw names:

```python
expected = {
    "aq_repaired_industry_relative_cash_accrual_quality",
    "aq_repaired_size_liquidity_residual_asset_growth_quality",
    "aq_repaired_balanced_cash_asset_quality",
}
```

Also assert all repaired rows keep `date == signal_date`, `signal_date > ann_date`, and contain no raw formula names.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen
```

Expected: import failure for `build_accounting_quality_statement_repaired_factor_frame`.

- [ ] **Step 3: Implement minimal repaired frame builder**

Add `build_accounting_quality_statement_repaired_factor_frame(raw_factor_frame, stock_basic, min_cross_section=6)`.

Implementation rules:

- Pivot raw factor rows by `date/asset_id/market/ann_date/end_date/signal_date`.
- Attach stock_basic industry.
- On each signal date, compute cross-sectional percentile ranks for:
  - `cashflow_minus_netprofit_to_assets_raw`
  - `low_asset_growth_quality_raw`
  - `earnings_cash_conversion_improvement_yoy_raw`
  - inverse of `working_capital_accruals_to_assets_raw`
- For industry-relative values, subtract each industry's date mean rank.
- For size/liquidity residual values, residualize rank values against available `log_circ_mv`, `log_total_mv`, `log_adv20`, `log_adv20_amount`, `turnover_rate_f`, `turnover_rate`.
- Emit three repaired factor names only.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen
```

Expected: OK.

### Task 2: Repaired Prescreen Mode And CLI

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py`
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Write failing tests**

Add tests that call `build_accounting_quality_statement_residual_ic_shape_prescreen(..., factor_mode="repaired")` and CLI `factor_mode="repaired"`, then assert:

- `result["factor_mode"] == "repaired"`
- candidate count is 3
- promotion remains blocked
- output CSV exists

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

Expected: unexpected keyword or missing CLI argument.

- [ ] **Step 3: Implement repaired mode**

Add `factor_mode` with allowed values `raw` and `repaired`. In repaired mode, call the new repaired frame builder after `_attach_market_context`, use repaired candidate specs, and set:

```python
result["factor_mode"] = "repaired"
result["source_context"]["candidate_family"] = "accounting_accruals_cashflow_quality_repaired"
```

CLI exposes:

```powershell
--factor-mode raw|repaired
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
```

Expected: OK.

### Task 3: Real 115-Symbol Repaired Prescreen And Reports

**Files:**
- Modify: `configs/accounting_quality_statement_smoke_plan_round237_20260625.json`
- Modify: `configs/accounting_quality_statement_backfill_round236_20260625.json`
- Modify: `docs/research/cn_stock_round239_accounting_quality_residual_ic_shape_prescreen_2026-06-25.md`
- Create: `docs/research/cn_stock_round240_accounting_quality_repaired_candidate_prescreen_2026-06-25.md`

- [ ] **Step 1: Run repaired prescreen**

Run `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py` with the same 115-symbol statement roots, bars roots, daily-basic roots, `--factor-mode repaired`, horizons 5 and 20, no final holdout, and output:

```text
data/reports/round240_accounting_quality_repaired_candidate_prescreen_115_symbol_20260625
```

- [ ] **Step 2: Update configs and docs**

Record candidate count, test count, FDR significant tests, neutral-gate pass tests, research leads, and promotion status.

- [ ] **Step 3: Verify**

Run:

```powershell
python -m json.tool configs\accounting_quality_statement_smoke_plan_round237_20260625.json > $null
python -m json.tool configs\accounting_quality_statement_backfill_round236_20260625.json > $null
python -m unittest tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen_cli
python -m py_compile src\quant_robot\ops\accounting_quality_statement_residual_ic_shape_prescreen.py scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py
```

Expected: JSON parses, tests OK, compile OK.

## Self-Review

- Spec coverage: this plan implements the next aligned action after raw accounting-quality failure: repair formulas, retest with the same IC/FDR/neutral gates, and keep promotion blocked.
- Placeholder scan: no TBD/TODO/fill-later placeholders.
- Type consistency: `factor_mode`, `build_accounting_quality_statement_repaired_factor_frame`, and repaired factor names are consistently named across tests, CLI, and implementation.
