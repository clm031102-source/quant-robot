# Round115 Public Alpha101 IC/Quantile/Turnover Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a long-cycle statistical prescreen for the fixed Round114 public Alpha101/Qlib-style candidates.

**Architecture:** Add a dedicated ops module for loading richer OHLCV bars and computing candidate factor values, then delegate IC/quantile/turnover summary to the existing capacity-safe prescreen summarizer. Add a CLI wrapper and a lightweight research report.

**Tech Stack:** Python, pandas, existing `make_forward_returns`, existing capacity-safe summarizer, `unittest`.

---

### Task 1: Unit Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_capacity_safe_prescreen.py`

- [ ] **Step 1: Write failing tests**

Test synthetic OHLCV bars produce all 10 candidate names and the prescreen blocks promotion while allowing research leads only.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_prescreen`

Expected: fail because the module does not exist.

### Task 2: CLI Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_capacity_safe_prescreen_cli.py`

- [ ] **Step 1: Write failing CLI test**

Test that the CLI writes JSON/Markdown/results CSV/IC CSV.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_prescreen_cli`

Expected: fail because the script does not exist.

### Task 3: Prescreen Implementation

**Files:**
- Create: `src/quant_robot/ops/public_alpha101_capacity_safe_prescreen.py`
- Create: `scripts/run_public_alpha101_capacity_safe_prescreen.py`

- [ ] **Step 1: Implement rich bar loader**

Read only `processed/bars` files when present and require `open`, `high`, `low`, `adj_close`, `volume`, `amount`, and `vwap`.

- [ ] **Step 2: Implement candidate factor matrix**

Compute the fixed 10 candidate names with signal-date-only rolling windows and capacity filters.

- [ ] **Step 3: Implement CLI and writer**

Write `public_alpha101_capacity_safe_prescreen.json`, `.md`, `public_alpha101_capacity_safe_prescreen_results.csv`, and `public_alpha101_capacity_safe_prescreen_ic_observations.csv`.

### Task 4: Runtime And Report

**Files:**
- Create: `docs/research/cn_stock_public_alpha101_capacity_safe_prescreen_round115_2026-06-22.md`

- [ ] **Step 1: Run prescreen**

Run the Round115 CLI against local processed CN stock bars. If full 2015-2025 is too slow, first run a verified sampled/smoke prescreen and leave the full long-cycle command as next active work.

- [ ] **Step 2: Verify**

Run unit tests, startup gate, project audit, `py_compile`, and `git diff --check`.

Commit step is deferred because current startup context says commits and pushes are not allowed.
