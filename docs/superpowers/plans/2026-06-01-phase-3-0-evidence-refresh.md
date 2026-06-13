# Phase 3.0 Evidence Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the blocked promotion review packet into an ordered local evidence-refresh plan.

**Architecture:** Add a pure ops planner, a CLI artifact writer, and GUI/API integration that all consume the same plan payload. Keep all actions local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest, local `http.server` GUI, vanilla HTML/CSS/JS.

---

### Task 1: Evidence Refresh Planner

**Files:**
- Create: `src/quant_robot/ops/evidence_refresh.py`
- Test: `tests/unit/test_evidence_refresh.py`

- [x] **Step 1: Write the failing test**

Verify that a blocked Phase 2.9 review packet becomes a Phase 3.0 plan with data quality, provider readiness, paper observation, duplicate resolution, and manual gate tracks.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_evidence_refresh`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.evidence_refresh'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_evidence_refresh_plan()`, ordered action generation, Markdown rendering, and artifact writing.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_evidence_refresh`

Expected: PASS.

### Task 2: Evidence Refresh CLI

**Files:**
- Create: `scripts/run_evidence_refresh.py`
- Test: `tests/unit/test_evidence_refresh_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_evidence_refresh()` reads a review packet and writes JSON, Markdown, and action CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_evidence_refresh_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_evidence_refresh'`.

- [x] **Step 3: Write minimal implementation**

Add CLI arguments for `--review-packet` and `--output-dir`. Rebuild the promotion review packet first when the default review JSON does not exist.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_evidence_refresh_cli`

Expected: PASS.

### Task 3: Core Check and GUI Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Modify: `src/quant_robot/gui/research_service.py`
- Modify: `src/quant_robot/gui/app.py`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Test: `tests/unit/test_check_plan.py`
- Test: `tests/unit/test_gui.py`

- [x] **Step 1: Write failing tests**

Verify that `evidence_refresh` appears after `promotion_review` in the check plan, the GUI service exposes refresh tracks, the HTTP route returns Phase 3.0, and the HTML contains evidence-refresh targets.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_check_plan tests.unit.test_gui`

Expected: FAIL with missing check-plan step, service function, route, and HTML targets.

- [x] **Step 3: Write minimal implementation**

Add `evidence_refresh` to `run_checks`, add `/api/promotion/evidence-refresh`, and render refresh status plus ordered action rows on the Promotion Ops page.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_check_plan tests.unit.test_gui`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Create: `docs/phase_3_0_evidence_refresh.md`

- [x] **Step 1: Run focused tests**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_evidence_refresh_cli tests.unit.test_check_plan tests.unit.test_gui`

Expected: PASS.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
node --check src\quant_robot\gui\static\app.js
python scripts\run_checks.py --execute
```

Expected: PASS, with `evidence_refresh` included after `promotion_review`.

- [ ] **Step 3: Run browser verification**

Open the GUI, click Promotion Ops, and verify the page shows Evidence Refresh and Refresh Actions with no console errors.

Blocked in this session because Playwright/npx launch was rejected by the environment usage limit. GUI HTML, service snapshot, and HTTP route coverage are verified by `tests.unit.test_gui`.
