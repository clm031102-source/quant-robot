# Round230 Liquidity Shock Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new CN stock factor-mining round that rotates away from failed moneyflow, public anomaly, and supertrend-style paths into a pre-registered OHLCV liquidity-shock recovery family, then run a long-cycle residual IC prescreen.

**Architecture:** The new factor source is pure OHLCV and produces fixed-form, public-method-inspired Amihud/liquidity-shock recovery candidates. The prescreen reuses the existing public-trend residual IC framework for labels, exposure controls, yearly shards, industry neutralization, residualization, and no-promotion policy.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot` factor, prescreen, startup-gate, family-rotation, and candidate-plan-gate modules.

---

### Task 1: Factor Source

**Files:**
- Create: `src/quant_robot/factors/liquidity_shock_recovery.py`
- Test: `tests/unit/test_liquidity_shock_recovery_factors.py`

- [ ] **Step 1: Write the failing test**

```python
def test_factor_builder_emits_fixed_liquidity_recovery_names():
    factors = compute_liquidity_shock_recovery_factors(_bars())
    assert set(factors["factor_name"]) == set(LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_liquidity_shock_recovery_factors`

Expected: import failure for `quant_robot.factors.liquidity_shock_recovery`.

- [ ] **Step 3: Write minimal implementation**

Create `LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES` and `compute_liquidity_shock_recovery_factors(bars, factor_names=None)`. Require `date`, `asset_id`, `market`, `adj_close`, `high`, `low`, `amount`; compute only lag-safe rolling features with no negative shifts.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_liquidity_shock_recovery_factors`

Expected: all tests pass.

### Task 2: Formal Registry Integration

**Files:**
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/audit/project_audit.py`
- Test: `tests/unit/test_research_pipeline.py`
- Test: `tests/unit/test_experiment_runner.py`
- Test: `tests/unit/test_project_audit.py`

- [ ] **Step 1: Write failing registry tests**

Add tests that `factor_source="liquidity_shock_recovery"` routes only the requested factor through pipeline precompute and project-audit registry.

- [ ] **Step 2: Run tests to verify they fail**

Run targeted unittest names for the three new tests.

Expected: unsupported factor source or missing import failure.

- [ ] **Step 3: Register source**

Import the new factor names and builder, add `liquidity_shock_recovery` to allowed no-input factor sources, pipeline factor computation, experiment precompute, and project-audit registered names.

- [ ] **Step 4: Run tests to verify they pass**

Run the same targeted tests.

### Task 3: Round230 Rotation and Candidate Gate

**Files:**
- Create: `configs/family_rotation_candidates_round230_liquidity_shock_recovery_20260624.json`
- Create: `configs/family_rotation_seed_round230_liquidity_shock_recovery_20260624.json`
- Create: `configs/factor_mining_candidate_plan_round230_liquidity_shock_recovery_20260624.json`
- Create: `docs/research/cn_stock_round230_liquidity_shock_recovery_preregistration_2026-06-24.md`

- [ ] **Step 1: Write configs**

Declare `liquidity_shock_recovery` as selected and hibernate the failed Round229 family unless a new orthogonal exposure repair exists.

- [ ] **Step 2: Run gates**

Run startup gate, family rotation decision, and candidate plan gate against the new configs.

Expected: research screen allowed; portfolio and promotion still blocked.

### Task 4: Residual Prescreen

**Files:**
- Create: `src/quant_robot/ops/liquidity_shock_recovery_residual_prescreen.py`
- Create: `scripts/run_liquidity_shock_recovery_residual_prescreen.py`
- Test: `tests/unit/test_liquidity_shock_recovery_residual_prescreen.py`
- Test: `tests/unit/test_liquidity_shock_recovery_residual_prescreen_cli.py`

- [ ] **Step 1: Write failing prescreen tests**

Assert the prescreen builds factor rows with `family="liquidity_shock_recovery"` and writes JSON/Markdown/CSV artifacts.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_liquidity_shock_recovery_residual_prescreen tests.unit.test_liquidity_shock_recovery_residual_prescreen_cli`

Expected: missing module or missing script failure.

- [ ] **Step 3: Implement prescreen wrapper**

Reuse existing sharded residual IC helpers, defer expensive reference construction until residual leads exist, forbid portfolio/promotion, and retag source context as Round230.

- [ ] **Step 4: Run tests to verify they pass**

Run the same prescreen tests.

### Task 5: Real Long-Cycle Run and Report

**Files:**
- Create: `docs/research/cn_stock_round230_liquidity_shock_recovery_residual_prescreen_2026-06-24.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`

- [ ] **Step 1: Run long-cycle sharded prescreen**

Run: `python scripts/run_liquidity_shock_recovery_residual_prescreen.py --sharded --output-dir data/reports/liquidity_shock_recovery_residual_prescreen_round230_20260624`

Expected: output JSON and CSV artifacts under `data/reports`, which remain out of Git.

- [ ] **Step 2: Write audit report**

Summarize candidate count, data window, residual leads, blockers, and next direction.

- [ ] **Step 3: Update startup protocol**

Point startup gate to the Round230 report and next Round231 direction.

- [ ] **Step 4: Verify**

Run JSON validation, targeted tests, startup gate, and `git diff --check` for scoped files.
