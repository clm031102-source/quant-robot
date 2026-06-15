# Phase 4.4 Data Gap Resolution Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a fillable local resolution CSV template and supported-status reference from the data-gap resolution ledger.

**Architecture:** Extend the existing data-gap resolution module and writer with pure template helpers and two CSV artifacts. Keep the existing CLI shape while adding outputs that can be fed back through `--resolution-file`.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Template Builder

**Files:**
- Modify: `src/quant_robot/ops/data_gap_resolution.py`
- Test: `tests/unit/test_data_gap_resolution.py`

- [x] **Step 1: Write the failing test**

Verify that a ledger can produce fillable resolution template rows with `gap_id`, `asset_id`, `symbol`, `missing_date`, `resolution_status`, blank `evidence_note`, reviewer fields, and local guidance. Verify status options include blocking semantics for each supported status.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: FAIL because the template helper functions do not exist.

- [x] **Step 3: Write minimal implementation**

Implement `build_resolution_template_rows()` and `resolution_status_options()`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: PASS.

### Task 2: Artifact Writer Integration

**Files:**
- Modify: `src/quant_robot/ops/data_gap_resolution.py`
- Modify: `tests/unit/test_data_gap_resolution_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_data_gap_resolution()` writes `gap_resolutions_template.csv` and `data_gap_resolution_status_options.csv`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: FAIL until the writer creates the two new files.

- [x] **Step 3: Write minimal implementation**

Update `write_data_gap_resolution_ledger()` to write the template and status-option CSVs.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/phase_4_2_data_gap_resolution_ledger.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_4_data_gap_resolution_template.md`

- [x] **Step 1: Regenerate data-gap artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Expected: writes ledger, rows, action queue, template, and status-option CSVs.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
git diff --check
```

Expected: PASS except known CRLF warnings from Git on this workspace.
