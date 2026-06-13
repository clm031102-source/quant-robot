# Phase 4.5 Data Gap Resolution Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report invalid, unknown, and duplicate data-gap resolution CSV rows instead of silently accepting or discarding them.

**Architecture:** Extend the data-gap resolution builder with resolution-row validation and write a validation CSV artifact. Keep the CLI interface unchanged and keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Validation Model

**Files:**
- Modify: `src/quant_robot/ops/data_gap_resolution.py`
- Test: `tests/unit/test_data_gap_resolution.py`

- [x] **Step 1: Write the failing test**

Verify that invalid statuses, unknown gap IDs, and duplicate gap IDs produce `resolution_validation` rows and summary counts, while invalid or unknown rows are not applied to ledger rows.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: FAIL because the ledger does not expose `resolution_validation`.

- [x] **Step 3: Write minimal implementation**

Implement resolution-row validation, keep first valid resolution row for a gap, ignore invalid and unknown rows, and attach validation summary/details to the ledger.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: PASS.

### Task 2: Validation Artifact

**Files:**
- Modify: `src/quant_robot/ops/data_gap_resolution.py`
- Modify: `tests/unit/test_data_gap_resolution_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_data_gap_resolution()` writes `data_gap_resolution_validation.csv`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: FAIL until the writer creates the validation CSV.

- [x] **Step 3: Write minimal implementation**

Update `write_data_gap_resolution_ledger()` to write validation rows.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/phase_4_2_data_gap_resolution_ledger.md`
- Modify: `docs/phase_4_4_data_gap_resolution_template.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_5_data_gap_resolution_validation.md`

- [x] **Step 1: Regenerate data-gap artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Expected: writes `data_gap_resolution_validation.csv` along with existing artifacts.

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
