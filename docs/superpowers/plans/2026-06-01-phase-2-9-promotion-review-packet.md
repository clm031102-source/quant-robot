# Phase 2.9 Promotion Review Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate an auditable local review packet for the selected promotion candidate.

**Architecture:** Add a pure ops service for packet assembly, a CLI for artifact writing, and GUI/API integration that consumes the same payload. Keep all behavior research-only and pre-API.

**Tech Stack:** Python 3.11+, pandas, unittest, local `http.server` GUI, vanilla HTML/CSS/JS.

---

### Task 1: Review Packet Service

**Files:**
- Create: `src/quant_robot/ops/review_packet.py`
- Test: `tests/unit/test_promotion_review_packet.py`

- [x] **Step 1: Write the failing test**

Verify that a Phase 2.8 operations console with one paper-ready candidate creates a Phase 2.9 packet with selected candidate, blocked manual-review gate, checklist rows, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_promotion_review_packet`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.review_packet'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_promotion_review_packet()`, checklist helpers, manual-review gate logic, Markdown rendering, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_promotion_review_packet`

Expected: PASS.

### Task 2: Review Packet CLI

**Files:**
- Create: `scripts/run_promotion_review.py`
- Test: `tests/unit/test_promotion_review_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_promotion_review()` reads `promotion_ops.json` and writes JSON, Markdown, and checklist CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_promotion_review_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_promotion_review'`.

- [x] **Step 3: Write minimal implementation**

Add CLI arguments for `--promotion-ops`, `--candidate-id`, and `--output-dir`. Rebuild Promotion Ops first when the default ops JSON does not exist.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_promotion_review_cli`

Expected: PASS.

### Task 3: Core Check and GUI Integration

**Files:**
- Modify: `scripts/run_checks.py`
- Modify: `src/quant_robot/gui/research_service.py`
- Modify: `src/quant_robot/gui/app.py`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Modify: `src/quant_robot/gui/static/styles.css`
- Test: `tests/unit/test_check_plan.py`
- Test: `tests/unit/test_gui.py`

- [x] **Step 1: Write failing tests**

Verify that `promotion_review` appears after `promotion_ops` in the check plan, the GUI service exposes a packet snapshot, the HTTP route returns Phase 2.9, and the HTML contains review packet targets.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_check_plan tests.unit.test_gui`

Expected: FAIL with missing check-plan step, missing service function, and missing route/HTML targets.

- [x] **Step 3: Write minimal implementation**

Add `promotion_review` to `run_checks`, add `/api/promotion/review`, and render review status, checklist, and Markdown on the Promotion Ops page.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_check_plan tests.unit.test_gui`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Create: `docs/phase_2_9_promotion_review_packet.md`

- [x] **Step 1: Run focused tests**

Run: `python -m unittest tests.unit.test_promotion_review_packet tests.unit.test_promotion_review_cli tests.unit.test_check_plan tests.unit.test_gui`

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

Expected: PASS, with `promotion_review` included after `promotion_ops`.

- [x] **Step 3: Run browser verification**

Open the GUI, click Promotion Ops, and verify the page shows Review Packet, Review Checklist, and Review Markdown with no console errors.
