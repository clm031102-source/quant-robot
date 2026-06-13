# Phase 4.0 Pre-API Readiness Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate Phase 3 local evidence into one pre-API readiness board with status, blockers, next local actions, and no-live-boundary evidence.

**Architecture:** Add a pure readiness board module, a CLI artifact writer, and integration into the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Readiness Board Service

**Files:**
- Create: `src/quant_robot/ops/pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board.py`

- [x] **Step 1: Write the failing test**

Verify that local evidence payloads produce a Phase 4.0 board with readiness items, blocker register rows, next local actions, boundary state, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.pre_api_readiness_board'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_pre_api_readiness_board()`, Markdown rendering, readiness items, blocker register rows, next-local-action rows, live-boundary state, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board`

Expected: PASS.

### Task 2: Readiness Board CLI

**Files:**
- Create: `scripts/run_pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_pre_api_readiness_board()` writes JSON, Markdown, readiness items CSV, blockers CSV, and next-actions CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_pre_api_readiness_board'`.

- [x] **Step 3: Write minimal implementation**

Read local evidence artifacts, build the board, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board_cli`

Expected: PASS.

### Task 3: Check Plan Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [x] **Step 1: Write failing test**

Verify that `run_checks.py` includes `pre_api_readiness_board` after `evidence_refresh`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: FAIL until the check-plan step is added.

- [x] **Step 3: Write minimal implementation**

Append `CheckStep("pre_api_readiness_board", [python_executable, "scripts/run_pre_api_readiness_board.py"])`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_check_plan`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_0_pre_api_readiness_board.md`

- [x] **Step 1: Run readiness board smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Expected: writes pre-API readiness board artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `pre_api_readiness_board` included after `evidence_refresh`.
