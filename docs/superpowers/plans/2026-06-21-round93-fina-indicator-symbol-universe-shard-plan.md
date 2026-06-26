# Round93 Fina Indicator Symbol Universe Shard Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact symbol-universe shard planner for larger `fina_indicator` backfills.

**Architecture:** Add a pure planner under `quant_robot.ops` and a thin CLI wrapper. The planner returns compact shard summaries rather than enumerating every symbol-period request.

**Tech Stack:** Python standard library, pandas, unittest, existing repo bootstrap.

---

### Task 1: Shard Planner

**Files:**
- Create: `tests/unit/test_fina_indicator_symbol_shard_plan.py`
- Create: `src/quant_robot/ops/fina_indicator_symbol_shard_plan.py`

- [ ] Write failing tests for deterministic shard splitting and request-budget blockers.
- [ ] Implement the planner.
- [ ] Run the tests to green.

### Task 2: Shard Plan CLI

**Files:**
- Create: `tests/unit/test_fina_indicator_symbol_shard_plan_cli.py`
- Create: `scripts/run_fina_indicator_symbol_shard_plan.py`

- [ ] Write failing CLI tests for symbol-file artifact generation.
- [ ] Implement the CLI.
- [ ] Run the tests to green.

### Task 3: Real Local Plan And Report

**Files:**
- Create: `docs/research/cn_stock_tushare_fina_indicator_symbol_universe_shard_plan_round93_2026-06-21.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] Generate a local shard plan from `data/processed/cn_stock_metadata/metadata/tushare_stock_basic`.
- [ ] Record symbol count, shard count, total requests, and first-shard request count.
- [ ] Advance startup gate to a first-shard backfill smoke only.

### Task 4: Verification

- [ ] Run focused tests.
- [ ] Run startup gate.
- [ ] Run project audit.
- [ ] Run `git diff --check`.
