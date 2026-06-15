# Phase 4.12 Pre-API Readiness Projection Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local projection pack that combines current readiness-board evidence with data-gap and provider-remediation rehearsal reductions.

**Architecture:** Add a pure projection module, a CLI artifact writer, and check-plan integration after `pre_api_readiness_board`. Keep projections separate from real evidence and preserve the no-live-boundary safety state.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Readiness Projection Service

**Files:**
- Create: `src/quant_robot/ops/readiness_projection.py`
- Test: `tests/unit/test_readiness_projection.py`

- [x] **Step 1: Write the failing test**

Build a projection from a small readiness board plus data-gap and provider-remediation rehearsals. Assert:

```python
self.assertEqual(pack["stage"], "phase_4_12_pre_api_readiness_projection_pack")
self.assertEqual(pack["summary"]["current_blockers"], 4)
self.assertEqual(pack["summary"]["total_rehearsal_delta"], 6)
self.assertEqual(pack["summary"]["projected_blocked_items"], 2)
self.assertFalse(pack["boundary"]["would_cross_live_boundary"])
self.assertEqual(deltas["data_gap_resolution"]["blocker_delta"], 2)
self.assertEqual(deltas["provider_remediation"]["blocker_delta"], 4)
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_readiness_projection
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_readiness_projection_pack()`, Markdown rendering, delta rows, residual rows, and `write_readiness_projection_pack()`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_readiness_projection
```

Expected: PASS.

### Task 2: Readiness Projection CLI

**Files:**
- Create: `scripts/run_readiness_projection.py`
- Test: `tests/unit/test_readiness_projection_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_readiness_projection(...)` writes JSON, Markdown, projection items CSV, deltas CSV, and residuals CSV.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_readiness_projection_cli
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read the three input JSON files, build the projection pack, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_readiness_projection_cli
```

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `readiness_projection` appears immediately after `pre_api_readiness_board` and before `blocker_worklist`.

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
CheckStep("readiness_projection", [python_executable, "scripts/run_readiness_projection.py"])
```

after `pre_api_readiness_board`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_check_plan
```

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase_4_12_pre_api_readiness_projection_pack.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, output artifacts, and interpretation of projected versus real evidence.

- [x] **Step 2: Regenerate real projection artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_readiness_projection.py --output-dir data\reports\readiness_projection
```

Expected: writes projection JSON, Markdown, items CSV, delta CSV, and residual CSV.

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
