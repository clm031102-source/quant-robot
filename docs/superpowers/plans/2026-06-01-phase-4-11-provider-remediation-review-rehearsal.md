# Phase 4.11 Provider Remediation Review Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local rehearsal pack that proves provider-remediation review rows can reduce blocking counts without changing real evidence.

**Architecture:** Add a pure rehearsal module, a CLI artifact writer, and check-plan integration after `provider_remediation`. Reuse Phase 4.10 review validation as the only way to apply sample review rows.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Provider Remediation Rehearsal Service

**Files:**
- Create: `src/quant_robot/ops/provider_remediation_rehearsal.py`
- Test: `tests/unit/test_provider_remediation_rehearsal.py`

- [x] **Step 1: Write the failing test**

Verify that provider evidence with `tushare`, `ccxt`, `yfinance`, and Parquet blockers produces:

```python
self.assertEqual(rehearsal["stage"], "phase_4_11_provider_remediation_review_rehearsal")
self.assertEqual(rehearsal["summary"]["source_blocking_remediation_items"], 5)
self.assertEqual(rehearsal["summary"]["sample_review_rows"], 2)
self.assertEqual(rehearsal["summary"]["rehearsed_blocking_remediation_items"], 3)
self.assertEqual(rehearsal["summary"]["blocker_delta"], 2)
self.assertEqual(rehearsal["sample_review_rows"][0]["review_status"], "accepted_out_of_scope")
self.assertEqual(rehearsal["readiness_projection"]["status"], "block")
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_rehearsal
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_provider_remediation_rehearsal()`, Markdown rendering, sample review-row generation, readiness projection, and `write_provider_remediation_rehearsal()`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_rehearsal
```

Expected: PASS.

### Task 2: Provider Remediation Rehearsal CLI

**Files:**
- Create: `scripts/run_provider_remediation_rehearsal.py`
- Test: `tests/unit/test_provider_remediation_rehearsal_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_provider_remediation_rehearsal(...)` writes JSON, Markdown, sample reviews CSV, rehearsed remediation items CSV, and summary CSV.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_rehearsal_cli
```

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read a provider evidence JSON, build the rehearsal, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_rehearsal_cli
```

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `provider_remediation_rehearsal` appears immediately after `provider_remediation`.

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
CheckStep("provider_remediation_rehearsal", [python_executable, "scripts/run_provider_remediation_rehearsal.py"])
```

after `provider_remediation`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_check_plan
```

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase_4_11_provider_remediation_review_rehearsal.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, output artifacts, default out-of-scope providers, and interpretation of before/after blocking counts.

- [x] **Step 2: Regenerate real rehearsal artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation_rehearsal.py --output-dir data\reports\provider_remediation_rehearsal
```

Expected: writes rehearsal JSON, Markdown, sample-review CSV, rehearsed-items CSV, and summary CSV.

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
