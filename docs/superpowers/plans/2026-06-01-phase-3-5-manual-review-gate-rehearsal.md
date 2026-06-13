# Phase 3.5 Manual Review Gate Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rehearse the manual review gate locally, list every clean-state requirement, and prove no broker/account/order boundary is crossed.

**Architecture:** Add a pure manual gate rehearsal module, a CLI artifact writer, and integration into Evidence Refresh plus the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Manual Review Rehearsal Service

**Files:**
- Create: `src/quant_robot/ops/manual_review_rehearsal.py`
- Test: `tests/unit/test_manual_review_rehearsal.py`

- [x] **Step 1: Write the failing test**

Verify that a blocked review packet plus local evidence produces a Phase 3.5 rehearsal with requirement rows, blockers, dry-run boundary state, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_manual_review_rehearsal`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.manual_review_rehearsal'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_manual_review_rehearsal()`, Markdown rendering, requirement rows, blockers, dry-run output, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_manual_review_rehearsal`

Expected: PASS.

### Task 2: Manual Review Rehearsal CLI

**Files:**
- Create: `scripts/run_manual_review_rehearsal.py`
- Test: `tests/unit/test_manual_review_rehearsal_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_manual_review_rehearsal()` writes JSON, Markdown, and requirements CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_manual_review_rehearsal_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_manual_review_rehearsal'`.

- [x] **Step 3: Write minimal implementation**

Read local review and evidence artifacts, build the rehearsal, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_manual_review_rehearsal_cli`

Expected: PASS.

### Task 3: Evidence Refresh and Check Plan Integration

**Files:**
- Modify: `src/quant_robot/ops/evidence_refresh.py`
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_evidence_refresh.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing tests**

Verify that Evidence Refresh recommends `run_manual_review_rehearsal.py` and that `run_checks.py` includes `manual_review_rehearsal` after `promotion_review`.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: FAIL until the command and check-plan step are added.

- [x] **Step 3: Write minimal implementation**

Insert `run_manual_review_rehearsal.py` into manual-review ordered actions and append a `manual_review_rehearsal` check step.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_3_5_manual_review_gate_rehearsal.md`

- [x] **Step 1: Run manual review rehearsal smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_manual_review_rehearsal.py --output-dir data\reports\manual_review_rehearsal
```

Expected: writes manual review rehearsal artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `manual_review_rehearsal` included after `promotion_review`.
