# Phase 4.6 Data Gap Resolution Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a local rehearsal pack showing how sample data-gap resolutions change blocking counts.

**Architecture:** Add a pure rehearsal module, a CLI artifact writer, and check-plan integration after `data_gap_resolution`. Keep all behavior local, deterministic, and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Rehearsal Service

**Files:**
- Create: `src/quant_robot/ops/data_gap_rehearsal.py`
- Test: `tests/unit/test_data_gap_rehearsal.py`

- [x] **Step 1: Write the failing test**

Verify that an audit with three gaps produces a Phase 4.6 rehearsal with two sample accepted rows, reduced blocking count, before/after summary, readiness projection, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_rehearsal`

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_data_gap_rehearsal()` and `write_data_gap_rehearsal()`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_rehearsal`

Expected: PASS.

### Task 2: Rehearsal CLI

**Files:**
- Create: `scripts/run_data_gap_rehearsal.py`
- Test: `tests/unit/test_data_gap_rehearsal_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_data_gap_rehearsal()` writes JSON, Markdown, sample resolution CSV, rehearsed rows CSV, and summary CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_rehearsal_cli`

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read a data-quality audit JSON, build the rehearsal, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_rehearsal_cli`

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `data_gap_rehearsal` appears immediately after `data_gap_resolution`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: FAIL until the check step is added.

- [x] **Step 3: Write minimal implementation**

Insert `CheckStep("data_gap_rehearsal", [python_executable, "scripts/run_data_gap_rehearsal.py"])`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_6_data_gap_resolution_rehearsal.md`

- [x] **Step 1: Regenerate rehearsal artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_rehearsal.py --output-dir data\reports\data_gap_rehearsal
```

Expected: writes rehearsal JSON, Markdown, sample resolution CSV, rehearsed rows CSV, and summary CSV.

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
