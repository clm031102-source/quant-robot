# Phase 4.1 Blocker Resolution Worklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the pre-API readiness board into a local blocker-resolution worklist with open work items and a deduplicated action queue.

**Architecture:** Add a pure blocker worklist module, a CLI artifact writer, and integration into the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Blocker Worklist Service

**Files:**
- Create: `src/quant_robot/ops/blocker_worklist.py`
- Test: `tests/unit/test_blocker_worklist.py`

- [x] **Step 1: Write the failing test**

Verify that a readiness board produces Phase 4.1 open work items, a deduplicated action queue, boundary state, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_blocker_worklist`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.blocker_worklist'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_blocker_worklist()`, Markdown rendering, work item rows, action queue rows, boundary state, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_blocker_worklist`

Expected: PASS.

### Task 2: Blocker Worklist CLI

**Files:**
- Create: `scripts/run_blocker_worklist.py`
- Test: `tests/unit/test_blocker_worklist_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_blocker_worklist()` writes JSON, Markdown, work items CSV, and action queue CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_blocker_worklist_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_blocker_worklist'`.

- [x] **Step 3: Write minimal implementation**

Read a readiness board from disk, build the worklist, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_blocker_worklist_cli`

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing test**

Verify that `run_checks.py` includes `blocker_worklist` after `pre_api_readiness_board`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: FAIL until the check-plan step is added.

- [x] **Step 3: Write minimal implementation**

Append `CheckStep("blocker_worklist", [python_executable, "scripts/run_blocker_worklist.py"])`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_1_blocker_resolution_worklist.md`

- [x] **Step 1: Run blocker worklist smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_blocker_worklist.py --output-dir data\reports\blocker_worklist
```

Expected: writes blocker worklist artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `blocker_worklist` included after `pre_api_readiness_board`.
