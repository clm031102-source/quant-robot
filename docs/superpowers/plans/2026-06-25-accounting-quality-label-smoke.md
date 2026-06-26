# Accounting Quality Label Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable PIT signal-date and forward-label alignment smoke for CN stock accounting-quality statement factors before any IC or portfolio read.

**Architecture:** Reuse the existing statement formula smoke for factor formulas and the existing `make_forward_returns` label helper for forward returns. The new tool computes statement factor rows dated on the first tradable date strictly after `ann_date`, aligns them to forward labels, and blocks same-day announcement trading, final-holdout leakage, low label coverage, and alignment violations.

**Tech Stack:** Python, pandas, unittest, project `DatasetStore`, local processed Tushare bars and statement inputs.

---

### Task 1: Add Core Label-Smoke Behavior

**Files:**
- Create: `src/quant_robot/ops/accounting_quality_statement_matrix_label_smoke.py`
- Test: `tests/unit/test_accounting_quality_statement_matrix_label_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
def test_builds_statement_factor_matrix_on_first_trade_after_ann_date_and_aligned_forward_labels(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        statement_root = root / "statement"
        bars_root = root / "bars"
        _write_statement_inputs(statement_root)
        _write_bars(bars_root)

        result = build_accounting_quality_statement_matrix_label_smoke(
            statement_roots=[statement_root],
            bars_roots=[bars_root],
            horizons=(5, 20),
            execution_lag=1,
            min_label_coverage=0.90,
        )

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
        self.assertGreater(result["summary"]["factor_value_rows"], 0)
        self.assertGreater(result["summary"]["label_aligned_rows"], 0)
        self.assertGreaterEqual(result["summary"]["label_coverage"], 0.90)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["execution_policy"]["ic_calculated"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_matrix_label_smoke
```

Expected: FAIL with import error because the new module/function does not exist.

- [ ] **Step 3: Implement minimal core module**

Implement:

```python
build_accounting_quality_statement_matrix_label_smoke(...)
compute_accounting_quality_statement_factor_frame(...)
write_accounting_quality_statement_matrix_label_smoke(...)
```

Required behavior:

- Load statement inputs from one or more roots.
- Deduplicate `asset_id/end_date/ann_date/report_type`.
- Compute the five formula values from `FORMULA_SPECS`.
- Map each statement row to `signal_date = first trade date strictly after ann_date`.
- Generate labels with `make_forward_returns`.
- Align on `date/signal_date`, `asset_id`, and `market`.
- Count violations: `signal_date <= ann_date`, `entry_date <= signal_date`, `exit_date <= entry_date`.
- Keep promotion, paper-ready, portfolio, and live trading blocked.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_matrix_label_smoke
```

Expected: PASS.

### Task 2: Add Blocker Tests

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_matrix_label_smoke.py`

- [ ] **Step 1: Add insufficient forward-label coverage test**

```python
def test_blocks_when_forward_labels_do_not_cover_factor_dates(self) -> None:
    ...
    result = build_accounting_quality_statement_matrix_label_smoke(..., min_label_coverage=0.90)
    self.assertFalse(result["summary"]["passes"])
    self.assertIn("label_coverage_below_threshold", result["summary"]["blockers"])
```

- [ ] **Step 2: Add final-holdout exclusion test**

```python
def test_excludes_final_holdout_dates_by_default(self) -> None:
    ...
    result = build_accounting_quality_statement_matrix_label_smoke(..., analysis_end_date="2025-12-31")
    self.assertTrue(result["summary"]["passes"])
    self.assertLessEqual(result["summary"]["max_signal_date"], "2025-12-31")
    self.assertFalse(result["holdout_policy"]["final_holdout_included"])
```

- [ ] **Step 3: Run tests red/green**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_matrix_label_smoke
```

Expected: new tests fail before implementation, then pass after implementing blockers.

### Task 3: Add CLI Wrapper

**Files:**
- Create: `scripts/run_accounting_quality_statement_matrix_label_smoke.py`
- Test: `tests/unit/test_accounting_quality_statement_matrix_label_smoke_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
def test_cli_writes_label_smoke_reports(self) -> None:
    result = run_accounting_quality_statement_matrix_label_smoke_cli(...)
    self.assertTrue(result["summary"]["passes"])
    self.assertTrue((output_dir / "accounting_quality_statement_matrix_label_smoke.json").exists())
    self.assertTrue((output_dir / "accounting_quality_statement_matrix_label_smoke.md").exists())
    self.assertTrue((output_dir / "accounting_quality_statement_matrix_candidate_summary.csv").exists())
```

- [ ] **Step 2: Implement CLI**

CLI flags:

```text
--statement-root
--bars-root
--output-dir
--analysis-start-date
--analysis-end-date
--include-final-holdout
--horizon
--execution-lag
--min-label-coverage
--allow-not-ready
```

- [ ] **Step 3: Verify**

Run:

```powershell
python -m unittest tests.unit.test_accounting_quality_statement_matrix_label_smoke tests.unit.test_accounting_quality_statement_matrix_label_smoke_cli
```

Expected: PASS.

### Task 4: Run on Current 115-Symbol Sample and Document

**Files:**
- Modify: `configs/accounting_quality_statement_smoke_plan_round237_20260625.json`
- Modify: `configs/accounting_quality_statement_backfill_round236_20260625.json`
- Modify: `docs/research/cn_stock_round237_accounting_quality_100_symbol_efficiency_audit_2026-06-25.md`
- Modify: `docs/research/cn_stock_round238_pre_mining_entry_gate_enforcement_2026-06-25.md`

- [ ] **Step 1: Run current-sample label smoke**

Use all completed statement roots through shard 6 offset 10 and CN stock bars roots:

```powershell
python scripts\run_accounting_quality_statement_matrix_label_smoke.py --statement-root ... --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round238_accounting_quality_statement_matrix_label_smoke_115_symbol_20260625 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.60 --allow-not-ready
```

- [ ] **Step 2: Update configs/reports**

Record:

- passes/blockers;
- signal-date rule;
- label coverage;
- alignment violations;
- factor rows and label rows;
- next allowed action.

- [ ] **Step 3: Verify**

Run:

```powershell
python -m json.tool configs\accounting_quality_statement_smoke_plan_round237_20260625.json > $null
python -m unittest tests.unit.test_accounting_quality_statement_matrix_label_smoke tests.unit.test_accounting_quality_statement_matrix_label_smoke_cli tests.unit.test_accounting_quality_statement_formula_smoke tests.unit.test_accounting_quality_statement_formula_smoke_cli
git diff --check -- src\quant_robot\ops\accounting_quality_statement_matrix_label_smoke.py scripts\run_accounting_quality_statement_matrix_label_smoke.py tests\unit\test_accounting_quality_statement_matrix_label_smoke.py tests\unit\test_accounting_quality_statement_matrix_label_smoke_cli.py configs\accounting_quality_statement_smoke_plan_round237_20260625.json docs\research\cn_stock_round238_pre_mining_entry_gate_enforcement_2026-06-25.md
```

Expected: JSON valid, tests pass, diff check has no whitespace errors.
