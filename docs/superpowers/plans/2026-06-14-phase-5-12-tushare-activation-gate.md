# Phase 5.12 Tushare Activation Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-only Tushare activation gate that chains recent data refresh, post-refresh replay, sample sufficiency, and iterative expansion into one auditable paper-continuation decision.

**Architecture:** Add a small `ops` pack builder for the gate decision and a script runner that orchestrates existing Phase 5.7-5.11 runners. Expose the generated pack through the existing GUI snapshot and HTTP route, then show it in the Daily Ops console alongside the prior sample gates.

**Tech Stack:** Python stdlib, pandas for CSV artifact writes, existing `unittest` suite, static HTML/JS GUI.

---

### Task 1: Gate Behavior Tests

**Files:**
- Create: `tests/unit/test_tushare_activation_gate.py`

- [x] **Step 1: Write the failing tests**

```python
pack = run_tushare_activation_gate(..., readiness={"ready": False, "missing": ["TUSHARE_TOKEN is not set"]})
self.assertEqual(pack["status"], "blocked_missing_readiness")
self.assertEqual(calls, [])
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m unittest tests.unit.test_tushare_activation_gate`
Expected: fails because `scripts.run_tushare_activation_gate` does not exist.

### Task 2: Ops Pack And Runner

**Files:**
- Create: `src/quant_robot/ops/tushare_activation_gate.py`
- Create: `scripts/run_tushare_activation_gate.py`

- [x] **Step 1: Implement pack builder**

Build `phase_5_12_tushare_activation_gate` with `status`, `decision`, `stage_ledger`, `next_actions`, `markdown`, and `live_boundary_allowed=false`.

- [x] **Step 2: Implement runner**

Read the profile observation pack, block early if Tushare readiness is missing, otherwise run Phase 5.7 -> 5.8 -> 5.9 -> 5.11 with existing runners and sub-report directories.

- [x] **Step 3: Verify tests pass**

Run: `.venv\Scripts\python.exe -m unittest tests.unit.test_tushare_activation_gate`
Expected: `OK`.

### Task 3: CLI And Check Plan

**Files:**
- Create: `tests/unit/test_tushare_activation_gate_cli.py`
- Modify: `scripts/run_checks.py`
- Modify: `tests/unit/test_check_plan.py`

- [x] **Step 1: Add CLI smoke test**

Run the script with `TUSHARE_TOKEN` blank and assert it writes a blocked pack without exposing secrets.

- [x] **Step 2: Add check-plan stage**

Insert `tushare_activation_gate` after `iterative_observation_expansion`.

### Task 4: GUI/API

**Files:**
- Modify: `src/quant_robot/gui/research_service.py`
- Modify: `src/quant_robot/gui/app.py`
- Modify: `src/quant_robot/gui/static/app.js`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `tests/unit/test_gui.py`

- [x] **Step 1: Add snapshot and HTTP route**

Expose `/api/risk/tushare-activation-gate`.

- [x] **Step 2: Add Daily Ops panel**

Show status, blockers, stage ledger, actions, and safety boundary.

### Task 5: Artifacts And Verification

**Files:**
- Create: `docs/phase_5_12_tushare_activation_gate.md`
- Generate: `data/reports/tushare_activation_gate/tushare_activation_gate_pack.json`
- Generate: `data/reports/tushare_activation_gate_fixture/tushare_activation_gate_pack.json`

- [x] **Step 1: Generate real blocked pack**

Run without relying on a raw token in files; expected status is blocked until `TUSHARE_TOKEN` is available in the environment.

- [x] **Step 2: Generate fixture success pack**

Run with `--source tushare-fixture --execute`; expected status is paper observation ready when the sample gate clears.

- [x] **Step 3: Verify**

Run targeted tests, full tests, compile, JS syntax check, and HTTP route smoke.
