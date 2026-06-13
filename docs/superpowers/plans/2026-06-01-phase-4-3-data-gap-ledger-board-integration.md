# Phase 4.3 Data Gap Ledger Board Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the pre-API readiness board consume the data-gap resolution ledger and expose unresolved ledger rows as board blockers.

**Architecture:** Extend the board builder with an optional ledger payload, extend the CLI with a default ledger path, and update docs to describe the integrated readiness track. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Board Builder Integration

**Files:**
- Modify: `src/quant_robot/ops/pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board.py`

- [x] **Step 1: Write the failing test**

Verify that a blocking data-gap ledger adds a `data_gap_resolution` readiness item, a `data_gap_resolution_blocking_gaps` blocker, and a local action command.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board`

Expected: FAIL until the builder accepts and uses `data_gap_resolution`.

- [x] **Step 3: Write minimal implementation**

Add the optional builder argument, readiness item, blocker mapping, recommended command, and action queue merge.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board`

Expected: PASS.

### Task 2: CLI Integration

**Files:**
- Modify: `scripts/run_pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board_cli.py`

- [x] **Step 1: Write the failing test**

Verify that the CLI reads a local data-gap resolution ledger and writes a board containing the new track.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board_cli`

Expected: FAIL until the CLI accepts `data_gap_resolution`.

- [x] **Step 3: Write minimal implementation**

Add `DEFAULT_DATA_GAP_RESOLUTION`, `--data-gap-resolution`, and pass the optional JSON into the board builder.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_pre_api_readiness_board_cli`

Expected: PASS.

### Task 3: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/phase_4_0_pre_api_readiness_board.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_4_3_data_gap_ledger_board_integration.md`

- [x] **Step 1: Regenerate integrated board**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Expected: the board includes `data_gap_resolution`.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS.
