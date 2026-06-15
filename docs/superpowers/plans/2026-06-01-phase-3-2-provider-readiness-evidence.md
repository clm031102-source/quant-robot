# Phase 3.2 Provider Readiness Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn provider-readiness blockers into local JSON/Markdown/CSV evidence that distinguishes dependency, token, adapter, and market coverage gaps.

**Architecture:** Add a pure provider evidence module, a CLI artifact writer, and integration into Evidence Refresh plus the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Provider Evidence Service

**Files:**
- Create: `src/quant_robot/ops/provider_evidence.py`
- Test: `tests/unit/test_provider_evidence.py`

- [x] **Step 1: Write the failing test**

Verify that a provider-status payload produces a Phase 3.2 evidence pack with normalized readiness labels, provider summary counts, market coverage rows, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_provider_evidence`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.provider_evidence'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_provider_evidence_pack()`, Markdown rendering, provider rows, market matrix rows, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_provider_evidence`

Expected: PASS.

### Task 2: Provider Evidence CLI

**Files:**
- Create: `scripts/run_provider_evidence.py`
- Test: `tests/unit/test_provider_evidence_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_provider_evidence()` writes JSON, Markdown, `provider_market_matrix.csv`, and a provider readiness CSV.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_provider_evidence_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_provider_evidence'`.

- [x] **Step 3: Write minimal implementation**

Read optional provider status from disk, build status locally when no file is supplied, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_provider_evidence_cli`

Expected: PASS.

### Task 3: Evidence Refresh and Check Plan Integration

**Files:**
- Modify: `src/quant_robot/ops/evidence_refresh.py`
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_evidence_refresh.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing tests**

Verify that Evidence Refresh recommends `run_provider_evidence.py` and that `run_checks.py` includes `provider_evidence` after `provider_status`.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: FAIL until the command and check-plan step are added.

- [x] **Step 3: Write minimal implementation**

Insert `run_provider_evidence.py` into provider-readiness ordered actions and append a `provider_evidence` check step.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_3_2_provider_readiness_evidence.md`

- [x] **Step 1: Run provider evidence smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_evidence.py --output-dir data\reports\provider_evidence
```

Expected: writes provider evidence artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `provider_evidence` included after `provider_status`.
