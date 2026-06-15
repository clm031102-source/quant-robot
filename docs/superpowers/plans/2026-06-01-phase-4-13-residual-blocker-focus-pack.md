# Phase 4.13 Residual Blocker Focus Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local focus pack that converts readiness projection residuals into prioritized root blocker work.

**Architecture:** Add a pure `quant_robot.ops.residual_blocker_focus` module, a CLI artifact writer, check-plan integration after `blocker_worklist`, documentation, and generated local artifacts. Keep it strictly research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Residual Focus Service

**Files:**
- Create: `src/quant_robot/ops/residual_blocker_focus.py`
- Test: `tests/unit/test_residual_blocker_focus.py`

- [x] **Step 1: Write the failing test**

Build a focus pack from a small projection pack and blocker worklist. Assert:

```python
self.assertEqual(pack["stage"], "phase_4_13_residual_blocker_focus_pack")
self.assertEqual(pack["summary"]["root_focus_items"], 2)
self.assertEqual(pack["summary"]["residual_blockers"], 7)
self.assertEqual(pack["summary"]["downstream_waits"], 1)
self.assertEqual(pack["summary"]["action_queue"], 4)
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_blocker_focus
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_residual_blocker_focus_pack()`, downstream wait mapping, focus action selection, Markdown rendering, and `write_residual_blocker_focus_pack()`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_blocker_focus
```

Expected: PASS.

### Task 2: Residual Focus CLI

**Files:**
- Create: `scripts/run_residual_blocker_focus.py`
- Test: `tests/unit/test_residual_blocker_focus_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_residual_blocker_focus(...)` writes JSON, Markdown, focus item CSV, downstream wait CSV, and action CSV.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_blocker_focus_cli
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read projection and worklist JSON inputs, build the pack, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_blocker_focus_cli
```

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `residual_blocker_focus` appears immediately after `blocker_worklist`.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_check_plan
```

Expected: FAIL until the check step is added.

- [x] **Step 3: Write minimal implementation**

Insert:

```python
CheckStep("residual_blocker_focus", [python_executable, "scripts/run_residual_blocker_focus.py"])
```

after `blocker_worklist`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_check_plan
```

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase_4_13_residual_blocker_focus_pack.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, output artifacts, and interpretation of focus priorities.

- [x] **Step 2: Generate real focus artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_blocker_focus.py --output-dir data\reports\residual_blocker_focus
```

Expected: writes focus JSON, Markdown, focus item CSV, downstream wait CSV, and action CSV.

- [x] **Step 3: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
git diff --check
```

Expected: PASS except known CRLF warnings from Git on this workspace.
