# Composite Risk Filter Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable CN stock factor source that combines Round55 `smart_money_reversal_value_20` and Round56 `anti_obv_breakout_low_tail_20` into composite bottom-exclusion risk-filter scores.

**Architecture:** Add one focused factor module that reuses existing factor builders, converts component values to same-date same-market ranks, and emits long-schema factor rows. Register the source through the research pipeline, experiment runner, CLI choices, desktop preflight, and project audit.

**Tech Stack:** Python, pandas, existing `quant_robot.factors` long-schema contract, `unittest`.

---

### Task 1: Factor Module

**Files:**
- Create: `src/quant_robot/factors/daily_basic_public_risk_filter_bridge.py`
- Test: `tests/unit/test_daily_basic_public_risk_filter_bridge_factors.py`

- [ ] Write tests for schema, rank combination behavior, past-only behavior, and unknown factor rejection.
- [ ] Implement `compute_daily_basic_public_risk_filter_bridge_factors(bars, daily_basic_inputs, factor_names=None)`.
- [ ] Export factor names:
  - `risk_filter_bridge_equal_20`
  - `risk_filter_bridge_agreement_20`
  - `risk_filter_bridge_anti_obv_weighted_20`
- [ ] Verify: `python -m unittest tests.unit.test_daily_basic_public_risk_filter_bridge_factors`.

### Task 2: Registry Wiring

**Files:**
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/audit/project_audit.py`
- Modify: `scripts/run_research_pipeline.py`
- Modify: `scripts/run_desktop_factor_validation.py`
- Test: existing targeted unit tests plus new source assertions.

- [ ] Register the new factor source as a daily-basic input source.
- [ ] Add precompute support in experiment grids.
- [ ] Add audit registry support.
- [ ] Verify targeted tests pass.

### Task 3: Round57 Config And Validation

**Files:**
- Create: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Create after results: `docs/research/cn_stock_composite_risk_filter_bridge_round57_2026-06-21.md`

- [ ] Run long-cycle grid with 3 bridge factors, top100, rebalance 5/10, cost 10 bps plus 20 bps impact.
- [ ] Run bottom-exclusion overlay for rebalance 5 and 10.
- [ ] Run costed bottom-exclusion portfolio for rebalance 5 and 10 with 10m liquidity floor.
- [ ] Record promotable, paper-ready, research lead, and rejected counts.

### Verification

- [ ] `python -m unittest tests.unit.test_daily_basic_public_risk_filter_bridge_factors`
- [ ] Targeted pipeline/runner/audit tests for the new factor source.
- [ ] `python scripts\run_project_audit.py --json`
- [ ] Startup gate points to the latest completed round before further mining.
