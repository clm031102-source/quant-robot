# Phase 3.1 Data Quality Gap Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn CN ETF aggregate missing-date blockers into exact local asset/date audit artifacts.

**Architecture:** Add a pure data audit module, a CLI artifact writer, and integration into Evidence Refresh plus the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Gap Audit Service

**Files:**
- Create: `src/quant_robot/data/gap_audit.py`
- Test: `tests/unit/test_data_quality_gap_audit.py`

- [x] **Step 1: Write the failing test**

Verify that a bars DataFrame with one missing date produces a Phase 3.1 audit with exact missing rows, coverage rows, repair actions, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_quality_gap_audit`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.data.gap_audit'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_data_quality_gap_audit()`, Markdown rendering, coverage rows, repair actions, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_quality_gap_audit`

Expected: PASS.

### Task 2: Gap Audit CLI

**Files:**
- Create: `scripts/run_data_quality_audit.py`
- Test: `tests/unit/test_data_quality_gap_audit_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_data_quality_audit()` writes JSON, Markdown, `missing_dates.csv`, and `coverage_by_asset.csv`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_data_quality_gap_audit_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_data_quality_audit'`.

- [x] **Step 3: Write minimal implementation**

Load processed bars when no DataFrame is injected, build the audit, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_data_quality_gap_audit_cli`

Expected: PASS.

### Task 3: Evidence Refresh and Check Plan Integration

**Files:**
- Modify: `src/quant_robot/ops/evidence_refresh.py`
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_evidence_refresh.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing tests**

Verify that Evidence Refresh recommends `run_data_quality_audit.py` before CSV refresh and that `run_checks.py` includes `data_quality_audit` after `data_catalog`.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: FAIL until the command and check-plan step are added.

- [x] **Step 3: Write minimal implementation**

Insert `run_data_quality_audit.py` into data-quality ordered actions and append a `data_quality_audit` check step.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Create: `docs/phase_3_1_data_quality_gap_audit.md`
- Create: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Run real CN ETF audit smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_quality_audit.py --data-root data\processed\etf_csv --market CN_ETF --output-dir data\reports\data_quality_gap_audit
```

Expected: writes exact missing-date artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `data_quality_audit` included after `data_catalog`.
