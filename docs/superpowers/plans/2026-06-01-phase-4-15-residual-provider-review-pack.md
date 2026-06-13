# Phase 4.15 Residual Provider Review Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local review pack for provider-remediation rows that remain blocking after rehearsal.

**Architecture:** Add a pure `quant_robot.ops.residual_provider_review` module, a CLI artifact writer, check-plan integration after `residual_data_gap_review`, documentation, and generated local artifacts.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Residual Provider Review Service

**Files:**
- Create: `src/quant_robot/ops/residual_provider_review.py`
- Test: `tests/unit/test_residual_provider_review.py`

- [x] **Step 1: Write the failing test**

Build a pack from a small provider rehearsal payload. Assert:

```python
self.assertEqual(pack["stage"], "phase_4_15_residual_provider_review_pack")
self.assertEqual(pack["summary"]["residual_remediation_items"], 2)
self.assertEqual(pack["summary"]["sample_cleared_remediation_items"], 1)
self.assertTrue(pack["summary"]["blocks_api_boundary_after_review"])
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_provider_review
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_residual_provider_review_pack()`, residual item extraction, review template creation, action queue creation, Markdown rendering, and `write_residual_provider_review_pack()`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_provider_review
```

Expected: PASS.

### Task 2: Residual Provider Review CLI

**Files:**
- Create: `scripts/run_residual_provider_review.py`
- Test: `tests/unit/test_residual_provider_review_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_residual_provider_review(...)` writes JSON, Markdown, residual item CSV, template CSV, action CSV, and status-options CSV.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_provider_review_cli
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read provider rehearsal JSON, optionally read focus JSON, build the pack, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_residual_provider_review_cli
```

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `residual_provider_review` appears immediately after `residual_data_gap_review`.

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
CheckStep("residual_provider_review", [python_executable, "scripts/run_residual_provider_review.py"])
```

after `residual_data_gap_review`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_check_plan
```

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase_4_15_residual_provider_review_pack.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, output artifacts, and interpretation of residual provider-remediation review rows.

- [x] **Step 2: Generate real review artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_provider_review.py --output-dir data\reports\residual_provider_review
```

Expected: writes residual review JSON, Markdown, items CSV, template CSV, action CSV, and status-options CSV.

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
