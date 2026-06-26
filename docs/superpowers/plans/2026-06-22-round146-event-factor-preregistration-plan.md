# Round146 Event Factor Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable Round146 CN stock event-factor preregistration and Tushare event-endpoint availability smoke gate after the Round145 daily-basic final-holdout failure.

**Architecture:** Keep this as a research gate, not a profitability claim. A small ops module defines curated event candidate specs, probes event endpoints through an injected adapter, and emits JSON/Markdown/CSV artifacts. The script wraps live Tushare calls without printing secrets.

**Tech Stack:** Python `unittest`, `pandas`, existing `scripts.bootstrap`, local `quant_robot.ops` pattern.

---

### Task 1: Event Candidate Preregistration Module

**Files:**
- Create: `src/quant_robot/ops/event_factor_preregistration.py`
- Test: `tests/unit/test_event_factor_preregistration.py`

- [x] **Step 1: Write the failing test**

Run: `python -m unittest tests.unit.test_event_factor_preregistration`

Expected: FAIL with `ModuleNotFoundError: No module named 'quant_robot.ops.event_factor_preregistration'`.

- [x] **Step 2: Implement the minimal module**

Create `EventFactorCandidateSpec`, `default_event_factor_candidate_specs`, `probe_event_endpoints`, `build_event_factor_preregistration`, `write_event_factor_preregistration`, and `render_markdown`.

- [x] **Step 3: Run the test**

Run: `python -m unittest tests.unit.test_event_factor_preregistration`

Expected: OK.

### Task 2: Live Tushare CLI

**Files:**
- Create: `scripts/run_event_factor_preregistration.py`
- Test: optional CLI unit test if the wrapper needs logic beyond argument parsing.

- [x] **Step 1: Add script wrapper**

The wrapper should use `TushareAdapter().client`, probe only a small sample, write artifacts under `data/reports/event_factor_preregistration_round146_20260622`, and print JSON.

- [x] **Step 2: Run live smoke**

Run:

```powershell
python scripts\run_event_factor_preregistration.py --output-dir data\reports\event_factor_preregistration_round146_20260622
```

Expected: JSON output with endpoint rows/columns, no token in stdout, no promotion allowed.

### Task 3: Round146 Report And Governance

**Files:**
- Create: `docs/research/cn_stock_event_factor_preregistration_round146_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`

- [x] **Step 1: Write report**

Summarize selected event candidates, available endpoints, blocked endpoints, and next gate.

- [x] **Step 2: Update startup next direction**

If event availability passes, set next direction to the event IC/coverage prescreen. If it fails, rotate away.

- [x] **Step 3: Verify**

Run targeted tests, startup gate, py_compile, and `git diff --check`.
