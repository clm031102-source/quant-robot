# Phase 3.4 Duplicate Canonical Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn duplicate candidate suppression into a stable canonical registry with explicit duplicate member rows and suppression reasons.

**Architecture:** Add a pure duplicate registry module, a CLI artifact writer, and integration into Evidence Refresh, Promotion Ops, Promotion Review Packet, and the core check plan. Keep all behavior local and research-only.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Duplicate Registry Service

**Files:**
- Create: `src/quant_robot/ops/duplicate_registry.py`
- Test: `tests/unit/test_duplicate_registry.py`

- [x] **Step 1: Write the failing test**

Verify that a promotion report produces a Phase 3.4 registry with canonical rows, duplicate members, summary counts, suppression reasons, safety text, and Markdown.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_duplicate_registry`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.duplicate_registry'`.

- [x] **Step 3: Write minimal implementation**

Implement `build_duplicate_registry()`, Markdown rendering, canonical rows, duplicate member rows, and artifact writer.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_duplicate_registry`

Expected: PASS.

### Task 2: Duplicate Registry CLI

**Files:**
- Create: `scripts/run_duplicate_registry.py`
- Test: `tests/unit/test_duplicate_registry_cli.py`

- [x] **Step 1: Write the failing test**

Verify that `run_duplicate_registry()` writes JSON, Markdown, canonical candidate CSV, and duplicate member CSV artifacts.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_duplicate_registry_cli`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_duplicate_registry'`.

- [x] **Step 3: Write minimal implementation**

Read a promotion report from disk, build the registry, write artifacts, and print a compact JSON summary.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_duplicate_registry_cli`

Expected: PASS.

### Task 3: Integration

**Files:**
- Modify: `src/quant_robot/ops/evidence_refresh.py`
- Modify: `src/quant_robot/ops/promotion_console.py`
- Modify: `src/quant_robot/ops/review_packet.py`
- Modify: `scripts/run_checks.py`
- Test: `tests/unit/test_evidence_refresh.py`
- Test: `tests/unit/test_check_plan.py`
- Test: `tests/unit/test_promotion_ops.py`
- Test: `tests/unit/test_promotion_review_packet.py`

- [x] **Step 1: Write failing tests**

Verify that Evidence Refresh recommends `run_duplicate_registry.py`, `run_checks.py` includes `duplicate_registry`, Promotion Ops exposes registry fields, and Review Packet carries the summary.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_evidence_refresh tests.unit.test_check_plan tests.unit.test_promotion_ops tests.unit.test_promotion_review_packet`

Expected: FAIL until the integrations are added.

- [x] **Step 3: Write minimal implementation**

Add the check-plan step, duplicate-resolution action, Promotion Ops registry fields, and Review Packet summary field.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_duplicate_registry tests.unit.test_duplicate_registry_cli tests.unit.test_evidence_refresh tests.unit.test_check_plan tests.unit.test_promotion_ops tests.unit.test_promotion_review_packet`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`
- Create: `docs/phase_3_4_duplicate_canonical_registry.md`

- [x] **Step 1: Run duplicate registry smoke**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_duplicate_registry.py --promotion-report data\reports\promotion_gate_cn_etf_candidate_search\promotion_report.json --output-dir data\reports\duplicate_registry
```

Expected: writes duplicate registry artifacts.

- [x] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: PASS, with `duplicate_registry` included after `promotion_ops`.
