# Phase 4.2 Data Gap Resolution Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert missing data-quality rows into a local resolution ledger with stable gap IDs, statuses, evidence notes, and blocker counts.

**Architecture:** Add a pure data-gap resolution module, a CLI artifact writer, and check-plan integration immediately after the data-quality audit. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Data Gap Resolution Service

**Files:**
- Create: `src/quant_robot/ops/data_gap_resolution.py`
- Test: `tests/unit/test_data_gap_resolution.py`

- [x] **Step 1: Write the failing test**

Verify that a data-quality audit produces Phase 4.2 ledger rows, stable gap IDs, default `needs_review` statuses, local-only commands, API-boundary blocker counts, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.data_gap_resolution'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_data_gap_resolution_ledger()`, Markdown rendering, stable gap IDs, optional resolution overrides, action queue rows, summary counts, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution`

Expected: PASS.

### Task 2: Data Gap Resolution CLI

**Files:**
- Create: `scripts/run_data_gap_resolution.py`
- Test: `tests/unit/test_data_gap_resolution_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_data_gap_resolution()` writes JSON, Markdown, ledger CSV, and action queue CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_data_gap_resolution'`.

- [x] **Step 3: Write minimal implementation**

Read a data-quality audit from disk, optionally read local resolution CSV rows, build the ledger, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_gap_resolution_cli`

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing test**

Verify that `run_checks.py` includes `data_gap_resolution` immediately after `data_quality_audit`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: FAIL until the check-plan step is added.

- [x] **Step 3: Write minimal implementation**

Insert `CheckStep("data_gap_resolution", [python_executable, "scripts/run_data_gap_resolution.py"])`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_2_data_gap_resolution_ledger.md`

- [x] **Step 1: Run data gap resolution smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Expected: writes data gap resolution artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `data_gap_resolution` included after `data_quality_audit`.
