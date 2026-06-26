# Round92 Fina Indicator Limited Backfill Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and verify a limited-symbol long-history `fina_indicator` backfill smoke path with explicit empty-response recording and resume safety.

**Architecture:** Extend the existing financial ingest module with a conservative `empty_response_policy` argument, leaving default failure behavior unchanged. Add a thin CLI that builds a request plan, enforces a budget, runs the ingest with `record` policy, and writes a small JSON/Markdown report.

**Tech Stack:** Python standard library, pandas, existing `DatasetStore`, existing `IngestManifest`, unittest.

---

### Task 1: Empty Response Recording

**Files:**
- Modify: `tests/unit/test_tushare_financial_inputs_ingest.py`
- Modify: `src/quant_robot/data/ingest/tushare_financial_inputs.py`

- [ ] Write a failing test proving mixed empty/non-empty requests complete under `empty_response_policy="record"`.
- [ ] Run `python -m unittest tests.unit.test_tushare_financial_inputs_ingest` and verify the new test fails.
- [ ] Implement `empty_response_policy` with accepted values `fail` and `record`.
- [ ] Record empty requests in the returned result and manifest rows as `0`.
- [ ] Run the test module and verify it passes.

### Task 2: Resume Recorded Empty Requests

**Files:**
- Modify: `tests/unit/test_tushare_financial_inputs_ingest.py`
- Modify: `src/quant_robot/data/ingest/tushare_financial_inputs.py`

- [ ] Write a failing test proving a completed zero-row raw partition is skipped on resume.
- [ ] Update resume logic to skip completed requests when the raw partition exists, even if it has zero rows.
- [ ] Run the test module and verify it passes.

### Task 3: Limited Smoke CLI

**Files:**
- Create: `tests/unit/test_fina_indicator_limited_backfill_smoke_cli.py`
- Create: `scripts/run_fina_indicator_limited_backfill_smoke.py`

- [ ] Write a failing CLI test proving the smoke wrapper writes a report and enforces request budget.
- [ ] Implement `run_fina_indicator_limited_backfill_smoke_cli`.
- [ ] Run the CLI test and verify it passes.

### Task 4: Real/Fixture Smoke And Report

**Files:**
- Create: `docs/research/cn_stock_tushare_fina_indicator_limited_backfill_smoke_round92_2026-06-21.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] Run fixture or real limited-symbol smoke under `data/processed/...`.
- [ ] Run PIT readiness audit against the smoke output.
- [ ] Write the Round92 report with exact request/row/readiness counts.
- [ ] Advance startup gate to the next safe direction only if smoke evidence is adequate.

### Task 5: Verification

**Files:**
- No additional files.

- [ ] Run focused tests for financial ingest, new CLI, startup gate, and project audit.
- [ ] Run `python scripts\run_project_audit.py --json`.
- [ ] Run `git diff --check`.
