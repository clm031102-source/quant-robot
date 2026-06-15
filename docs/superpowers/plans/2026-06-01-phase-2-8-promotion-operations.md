# Phase 2.8 Promotion Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Phase 2.8 operations entry point, then prepare CN ETF provider ingestion and paper execution realism.

**Architecture:** Add a small operations service that aggregates existing reports without mutating research outputs. Extend the Tushare adapter and existing ingest pipeline for `CN_ETF`. Extend paper simulation with optional execution-block events while preserving all existing outputs.

**Tech Stack:** Python 3.11+, pandas, unittest, local `http.server` GUI.

---

### Task 1: Promotion Operations Summary

**Files:**
- Create: `src/quant_robot/ops/__init__.py`
- Create: `src/quant_robot/ops/promotion_console.py`
- Test: `tests/unit/test_promotion_ops.py`

- [x] **Step 1: Write the failing test**

Verify that a promotion report with one `paper_ready` candidate and one duplicate candidate produces a Phase 2.8 console payload with blockers and next actions.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_promotion_ops`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_promotion_operations_console()` with summary, top candidate, blockers, duplicate clusters, evidence status, next actions, and research-only safety text.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_promotion_ops`

Expected: PASS.

### Task 2: GUI API Entry Point

**Files:**
- Modify: `src/quant_robot/gui/research_service.py`
- Modify: `src/quant_robot/gui/app.py`
- Test: `tests/unit/test_gui.py`

- [x] **Step 1: Write the failing test**

Verify that `build_promotion_ops_snapshot()` and `/api/promotion/ops` return `stage=phase_2_8_promotion_operations` and keep `live_review_allowed=false`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_gui`

Expected: FAIL before the function and route exist.

- [x] **Step 3: Write minimal implementation**

Add the service wrapper, default report paths, missing-report fallback, and HTTP route.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_gui`

Expected: PASS.

### Task 3: CN ETF Tushare Provider Path

**Files:**
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Modify: `src/quant_robot/data/provider_status.py`
- Modify: `src/quant_robot/data/ingest/tushare_pipeline.py`
- Modify: `scripts/ingest_data.py`
- Test: `tests/unit/test_tushare_adapter.py`
- Test: `tests/unit/test_provider_status.py`
- Test: `tests/unit/test_tushare_ingest_pipeline.py`

- [x] **Step 1: Write failing tests**

Verify that `CN_ETF` uses `fund_daily`, provider status lists Tushare `CN_ETF` as implemented, and ingest writes `market=CN_ETF` processed bars.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_tushare_adapter tests.unit.test_provider_status tests.unit.test_tushare_ingest_pipeline`

Expected: FAIL with missing ETF methods and unsupported `market` argument.

- [x] **Step 3: Write minimal implementation**

Route ETF fetches to `fund_daily`, add `fetch_etf_daily_by_trade_date()`, keep old CN manifest keys, and map ETF symbols to `CN_ETF_<exchange>_<code>`.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_tushare_adapter tests.unit.test_provider_status tests.unit.test_tushare_ingest_pipeline`

Expected: PASS.

### Task 4: Paper Execution Constraints

**Files:**
- Modify: `src/quant_robot/paper/simulator.py`
- Test: `tests/unit/test_paper_simulation.py`

- [x] **Step 1: Write the failing test**

Verify that suspended and limit-up execution bars block fills and record `execution_events`.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_paper_simulation`

Expected: FAIL with missing `execution_events`.

- [x] **Step 3: Write minimal implementation**

Carry optional execution columns into execution-day price rows, block simulated fills, record events, and write `execution_events.csv`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_paper_simulation`

Expected: PASS.

### Task 5: Operations Artifact and GUI Surface

**Files:**
- Create: `scripts/run_promotion_ops.py`
- Modify: `scripts/run_checks.py`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Test: `tests/unit/test_promotion_ops_cli.py`
- Test: `tests/unit/test_check_plan.py`
- Test: `tests/unit/test_gui.py`

- [x] **Step 1: Write failing tests**

Verify that the CLI writes `promotion_ops.json`, `promotion_ops_candidates.csv`, and `promotion_ops_actions.csv`; verify `run_checks.py` includes `promotion_ops`; verify the local GUI HTML includes promotion operation table/list targets.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_promotion_ops_cli tests.unit.test_check_plan tests.unit.test_gui`

Expected: FAIL with missing `scripts.run_promotion_ops`, missing check-plan step, and missing promotion HTML targets.

- [x] **Step 3: Write minimal implementation**

Add `scripts/run_promotion_ops.py`, append `promotion_ops` to the local check plan, and add the Promotion Ops GUI page with metrics, blockers, next actions, candidate evidence, and duplicate clusters.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_promotion_ops_cli tests.unit.test_check_plan tests.unit.test_gui`

Expected: PASS.
