# Phase 3.3 Paper Observation Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn local paper-batch results into observation evidence with candidate windows, guard/execution events, risk-profile comparison, and metric trends.

**Architecture:** Add a pure paper observation module, a CLI artifact writer, and integration into Evidence Refresh plus the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Paper Observation Service

**Files:**
- Create: `src/quant_robot/ops/paper_observation.py`
- Test: `tests/unit/test_paper_observation.py`

- [x] **Step 1: Write the failing test**

Verify that a paper-batch payload plus candidate artifacts produces a Phase 3.3 pack with observation windows, guard summaries, execution summaries, risk-profile comparison, metric trends, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_paper_observation`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.paper_observation'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_paper_observation_pack()`, Markdown rendering, candidate rows, risk-profile comparison, metric trends, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_paper_observation`

Expected: PASS.

### Task 2: Paper Observation CLI

**Files:**
- Create: `scripts/run_paper_observation.py`
- Test: `tests/unit/test_paper_observation_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_paper_observation()` writes JSON, Markdown, candidate CSV, risk-profile CSV, and trend CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_paper_observation_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_paper_observation'`.

- [x] **Step 3: Write minimal implementation**

Read a paper-batch summary from disk, load candidate artifact files, build the observation pack, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_paper_observation_cli`

Expected: PASS.

### Task 3: Evidence Refresh and Check Plan Integration

**Files:**
- Modify: `src/quant_robot/ops/evidence_refresh.py`
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_evidence_refresh.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing tests**

Verify that Evidence Refresh recommends `run_paper_observation.py` and that `run_checks.py` includes `paper_observation` after `paper_simulation`.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: FAIL until the command and check-plan step are added.

- [x] **Step 3: Write minimal implementation**

Insert `run_paper_observation.py` into paper-observation ordered actions and append a `paper_observation` check step.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_3_3_paper_observation_extension.md`

- [x] **Step 1: Run paper observation smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_observation.py --paper-batch-summary data\reports\paper_batch_cn_etf_candidate_search\paper_batch_summary.json --output-dir data\reports\paper_observation
```

Expected: writes paper observation artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `paper_observation` included after `paper_simulation`.
