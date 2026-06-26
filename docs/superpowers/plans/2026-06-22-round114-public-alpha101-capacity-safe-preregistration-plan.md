# Round114 Public Alpha101 Capacity-Safe Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable Round114 preregistration step for curated public Alpha101/Qlib-style CN stock factor candidates.

**Architecture:** Add a focused ops module that returns a structured preregistration packet and writes JSON/Markdown/CSV artifacts. Add a CLI wrapper matching prior preregistration scripts. Update the startup gate after Round114 so the next action is Round115 prescreen, not a portfolio grid.

**Tech Stack:** Python standard library, existing `CapacitySafePriceVolumeCandidateSpec`, `unittest`, existing startup gate CLI.

---

### Task 1: Preregistration Unit Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_capacity_safe_preregistration.py`

- [ ] **Step 1: Write failing tests**

Test that the builder registers at least 10 unique CN stock candidates, includes Alpha101/Qlib public references, blocks promotion, records the Round113 source audit, and sets Round115 as the next direction.

- [ ] **Step 2: Run test to verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_preregistration`

Expected: fail with `ModuleNotFoundError` for the missing ops module.

### Task 2: CLI Unit Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_capacity_safe_preregistration_cli.py`

- [ ] **Step 1: Write failing CLI test**

Test that the CLI writes `public_alpha101_capacity_safe_preregistration.json`, `.md`, and candidate `.csv`, and that the JSON preserves `round115_public_alpha101_ic_quantile_turnover_prescreen`.

- [ ] **Step 2: Run test to verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_preregistration_cli`

Expected: fail with missing script or missing module.

### Task 3: Ops Module

**Files:**
- Create: `src/quant_robot/ops/public_alpha101_capacity_safe_preregistration.py`

- [ ] **Step 1: Implement candidate specs**

Reuse `CapacitySafePriceVolumeCandidateSpec` and create 10 curated candidates with public-source tags, capacity filters, and no promotion/portfolio permissions.

- [ ] **Step 2: Implement writer and Markdown renderer**

Write JSON/Markdown/CSV under the selected output directory. Markdown must list source audit, public reference method, candidate table, and next direction.

- [ ] **Step 3: Run unit tests**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_preregistration`

Expected: pass.

### Task 4: CLI Wrapper

**Files:**
- Create: `scripts/run_public_alpha101_capacity_safe_preregistration.py`

- [ ] **Step 1: Implement CLI**

Match prior preregistration CLIs with `--output-dir`, `--min-candidates`, and `--allow-not-ready`.

- [ ] **Step 2: Run CLI test**

Run: `python -m unittest tests.unit.test_public_alpha101_capacity_safe_preregistration_cli`

Expected: pass.

### Task 5: Startup Gate Advancement

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Update test expectations first**

Expect `source_audit` to point to Round114 report and `next_direction` to point to `round115_public_alpha101_ic_quantile_turnover_prescreen`.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_is_runnable`

Expected: fail until config is advanced.

- [ ] **Step 3: Update config**

Add confirmations for Round114 preregistration, add Round115 prescreen requirements, and reject direct Alpha101 portfolio-grid/promotion directions.

### Task 6: Round114 Execution And Verification

**Files:**
- Create: `docs/research/cn_stock_public_alpha101_capacity_safe_preregistration_round114_2026-06-22.md`
- Write ignored runtime artifacts under `data/reports/public_alpha101_capacity_safe_preregistration_round114_20260622`.

- [ ] **Step 1: Run real preregistration CLI**

Run: `python scripts\run_public_alpha101_capacity_safe_preregistration.py --output-dir data\reports\public_alpha101_capacity_safe_preregistration_round114_20260622 --min-candidates 10`

- [ ] **Step 2: Write lightweight research report**

Summarize candidate count, gates, public references, why promotion is blocked, and Round115 next action.

- [ ] **Step 3: Fresh verification**

Run unit tests, startup gate, project audit, and `git diff --check`.

Commit step is intentionally deferred because current startup context says commits and pushes are not allowed for this task.
