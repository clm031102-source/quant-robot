# Phase 4.7 Provider Remediation Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert provider evidence into a local remediation matrix with blocker types, review hints, and verification commands.

**Architecture:** Add a pure provider-remediation module, a CLI writer, and check-plan integration after `provider_evidence`. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Provider Remediation Service

**Files:**
- Create: `src/quant_robot/ops/provider_remediation.py`
- Test: `tests/unit/test_provider_remediation.py`

- [x] **Step 1: Write the failing test**

Verify that provider evidence with missing dependency, missing token, planned adapter, and Parquet blocker produces remediation items with blocker types, local verification commands, safety text, and summary counts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_provider_remediation`

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Implement `build_provider_remediation_matrix()` and `write_provider_remediation_matrix()`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_provider_remediation`

Expected: PASS.

### Task 2: Provider Remediation CLI

**Files:**
- Create: `scripts/run_provider_remediation.py`
- Test: `tests/unit/test_provider_remediation_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_provider_remediation()` writes JSON, Markdown, remediation items CSV, and summary CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_provider_remediation_cli`

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Write minimal implementation**

Read a provider evidence JSON, build the remediation matrix, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_provider_remediation_cli`

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write the failing test**

Verify that `provider_remediation` appears immediately after `provider_evidence`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: FAIL until the check step is added.

- [x] **Step 3: Write minimal implementation**

Insert `CheckStep("provider_remediation", [python_executable, "scripts/run_provider_remediation.py"])`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_7_provider_remediation_matrix.md`

- [x] **Step 1: Regenerate provider remediation artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Expected: writes remediation JSON, Markdown, items CSV, and summary CSV.

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
