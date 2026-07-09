# Round691 Financial Reporting Timeliness Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PIT-safe `financial_reporting_timeliness` residual IC shape prescreen mode for the five Round691 pre-registered CN stock candidates.

**Architecture:** Reuse the existing accounting-quality statement matrix and residual IC shape prescreen path. The new mode converts already PIT-aligned statement rows into five timeliness factor rows, then sends them through the established neutral IC, FDR, quantile shape, and no-promotion reporting pipeline.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops.accounting_quality_statement_residual_ic_shape_prescreen`, existing CLI `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`.

---

### Task 1: Add Failing Unit Tests For The Timeliness Factor Mode

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Write the failing tests**

Add imports and tests equivalent to:

```python
from quant_robot.ops.accounting_quality_statement_matrix_label_smoke import (
    compute_accounting_quality_statement_factor_frame,
)
from quant_robot.ops.accounting_quality_statement_residual_ic_shape_prescreen import (
    build_financial_reporting_timeliness_factor_frame,
)

def test_financial_reporting_timeliness_factor_frame_builds_preregistered_candidates(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        statement_root = root / "statement"
        bars_root = root / "bars"
        assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
        _write_statement_inputs(statement_root, _timeliness_statement_rows(assets))
        _write_bars(bars_root, _bar_rows(assets))

        raw = compute_accounting_quality_statement_factor_frame(
            statement_roots=[statement_root],
            bars_roots=[bars_root],
        )
        frame = build_financial_reporting_timeliness_factor_frame(raw, min_cross_section=4)

    self.assertEqual(
        set(frame["factor_name"].unique()),
        {
            "frt_reporting_lag_short",
            "frt_reporting_lag_improvement_4q",
            "frt_reporting_lag_stability_8q",
            "frt_early_report_quality_combo",
            "frt_late_reporter_risk_avoidance",
        },
    )
    self.assertTrue((frame["date"] == frame["signal_date"]).all())
    self.assertTrue((frame["signal_date"] > frame["ann_date"]).all())
    self.assertTrue(frame["factor_value"].notna().all())
    self.assertIn("reporting_lag_days", frame.columns)

def test_builds_financial_reporting_timeliness_mode_without_old_candidates(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        statement_root = root / "statement"
        bars_root = root / "bars"
        daily_basic_root = root / "daily_basic"
        stock_basic_root = root / "stock_basic"
        assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
        _write_statement_inputs(statement_root, _timeliness_statement_rows(assets))
        _write_bars(bars_root, _bar_rows(assets))
        _write_daily_basic(daily_basic_root, assets)
        _write_stock_basic(stock_basic_root, assets)

        result = build_accounting_quality_statement_residual_ic_shape_prescreen(
            statement_roots=[statement_root],
            bars_roots=[bars_root],
            stock_basic_path=stock_basic_root,
            daily_basic_roots=[daily_basic_root],
            horizons=(5,),
            factor_mode="financial_reporting_timeliness",
            min_cross_section=4,
            min_ic_observations=2,
            min_neutral_ic_t_stat=0.0,
        )

    self.assertEqual(result["factor_mode"], "financial_reporting_timeliness")
    self.assertEqual(result["summary"]["candidate_count"], 5)
    self.assertEqual(result["source_context"]["candidate_family"], "financial_reporting_timeliness")
    self.assertFalse(result["promotion_policy"]["promotion_allowed"])
```

Add `_timeliness_statement_rows(asset_ids)` in the same test file. It must produce at least five quarterly observations per asset with varying `ann_date - end_date` lags, and the same financial columns used by existing statement formula tests.

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py -q
```

Expected: FAIL because `build_financial_reporting_timeliness_factor_frame` is not implemented and `factor_mode="financial_reporting_timeliness"` is not accepted.

### Task 2: Implement The Timeliness Factor Builder And Prescreen Mode

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`

- [ ] **Step 1: Add constants and mode wiring**

Add:

```python
NEXT_DIRECTION_FINANCIAL_REPORTING_TIMELINESS_WITH_LEADS = "round692_financial_reporting_timeliness_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_FINANCIAL_REPORTING_TIMELINESS_WITHOUT_LEADS = "round692_rotate_or_repair_financial_reporting_timeliness_after_residual_ic_shape_failure"
FINANCIAL_REPORTING_TIMELINESS_FACTOR_NAMES = (
    "frt_reporting_lag_short",
    "frt_reporting_lag_improvement_4q",
    "frt_reporting_lag_stability_8q",
    "frt_early_report_quality_combo",
    "frt_late_reporter_risk_avoidance",
)
```

Include `"financial_reporting_timeliness"` in `valid_factor_modes`, the error message, and the mode branch:

```python
elif factor_mode == "financial_reporting_timeliness":
    context_factor_frame = build_financial_reporting_timeliness_factor_frame(
        context_factor_frame,
        min_cross_section=min_cross_section,
    )
    candidate_specs = _financial_reporting_timeliness_candidate_specs()
    expected_candidate_count = len(candidate_specs)
```

After `result.update(...)`, attach source context:

```python
if factor_mode == "financial_reporting_timeliness":
    result["source_context"]["candidate_family"] = "financial_reporting_timeliness"
    result["source_context"]["hypothesis_source"] = (
        "Round691 preregistered PIT financial reporting timeliness candidates; "
        "values become tradable only on first trading date strictly after ann_date"
    )
    result["source_context"]["timeliness_candidate_coverage"] = _factor_symbol_coverage(factor_frame)
    result["source_context"]["timeliness_year_coverage"] = _factor_coverage_by_end_year(factor_frame)
    result["summary"]["source_raw_factor_rows_before_financial_reporting_timeliness"] = int(len(raw_factor_frame))
    result["summary"]["next_direction"] = (
        NEXT_DIRECTION_FINANCIAL_REPORTING_TIMELINESS_WITH_LEADS
        if int(result["summary"].get("research_lead_count", 0))
        else NEXT_DIRECTION_FINANCIAL_REPORTING_TIMELINESS_WITHOUT_LEADS
    )
```

- [ ] **Step 2: Add factor builder and candidate specs**

Implement:

```python
def build_financial_reporting_timeliness_factor_frame(
    raw_factor_frame: pd.DataFrame,
    *,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    ...
```

The function must:
- pivot with `_wide_raw_accounting_quality_frame`;
- compute `reporting_lag_days = ann_date - end_date`;
- reject rows where `signal_date <= ann_date`;
- create exactly the five pre-registered candidates;
- use only current and prior reporting lags by asset;
- preserve `date == signal_date`, `ann_date`, `end_date`, `asset_id`, `market`, and existing exposure columns;
- add `reporting_lag_days` to emitted rows;
- avoid portfolio, promotion, or final holdout behavior.

Implement `_financial_reporting_timeliness_candidate_specs()`, `_factor_symbol_coverage()`, and `_factor_coverage_by_end_year()`.

- [ ] **Step 3: Run unit tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py -q
```

Expected: PASS.

### Task 3: Add CLI Support And CLI Test Coverage

**Files:**
- Modify: `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py`

- [ ] **Step 1: Write CLI failing test**

Add a test that calls `run_accounting_quality_statement_residual_ic_shape_prescreen_cli(..., factor_mode="financial_reporting_timeliness", ...)`, writes outputs, asserts candidate count 5, and asserts promotion stays blocked.

- [ ] **Step 2: Run CLI test to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py -q
```

Expected: FAIL before CLI choices include the new factor mode.

- [ ] **Step 3: Add CLI choice**

Add `"financial_reporting_timeliness"` to `--factor-mode` choices.

- [ ] **Step 4: Run CLI tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py -q
```

Expected: PASS.

### Task 4: Run Round691 Prescreen And Document Evidence

**Files:**
- Create: `docs/research/cn_stock_round691_financial_reporting_timeliness_prescreen_2026-07-09.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Run fixed 5D/20D Round691 prescreen**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --factor-mode financial_reporting_timeliness --horizon 5 --horizon 20 --output-dir data\reports\round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709 --allow-not-ready
```

If the broad `data\processed` root is too expensive or includes incompatible rows, use the known financial statement roots from the source audit while keeping the same fixed horizons and output directory.

- [ ] **Step 2: Summarize prescreen evidence**

Write a lightweight Markdown summary with:
- command;
- gate statuses and blockers;
- manifest warnings;
- candidate count and result counts;
- PIT alignment proof (`signal_date > ann_date`);
- no portfolio grid, no promotion, no final holdout;
- next direction from the report.

- [ ] **Step 3: Final verification before commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py -q
.\.venv\Scripts\python.exe -m json.tool configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json > $null
git diff --check
git status --short
```

Expected: tests pass, JSON parses, diff check exits 0, and only source/test/docs/config lightweight files are modified.

### Task 5: Commit Allowed Source And Summary Files

**Files:**
- Stage only source code, tests, docs, and configs.

- [ ] **Step 1: Review changed paths**

Run:

```powershell
git status --short
git diff --stat
git diff --cached --stat
```

- [ ] **Step 2: Commit**

Stage allowed files and commit:

```powershell
git add src\quant_robot\ops\accounting_quality_statement_residual_ic_shape_prescreen.py scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py docs\superpowers\plans\2026-07-09-round691-financial-reporting-timeliness-prescreen.md docs\research\cn_stock_round691_financial_reporting_timeliness_prescreen_2026-07-09.md docs\research\CURRENT_RESEARCH_INDEX.md
git commit -m "Add Round691 financial reporting timeliness prescreen"
```
