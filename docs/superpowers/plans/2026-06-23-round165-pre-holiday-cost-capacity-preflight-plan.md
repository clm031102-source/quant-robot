# Round165 Pre-Holiday Cost Capacity Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the single Round164 residual research lead `pre_holiday_liquidity_avoidance_5_3` into a narrow cost/capacity portfolio preflight without allowing promotion.

**Architecture:** Rebuild the Round164 calendar feature frame, isolate the frozen lead, industry-neutralize and residualize it, then run a fixed TopN cost/capital stress using the existing `run_factor_backtest` engine. The output decides only whether a later walk-forward validation is allowed.

**Tech Stack:** Python, pandas, existing factor backtest engine, Round164 calendar residual helpers, JSON/Markdown/CSV outputs, `unittest`.

---

### Task 1: Tests First

**Files:**
- Create: `tests/unit/test_cn_calendar_pre_holiday_cost_capacity_preflight.py`
- Create: `tests/unit/test_cn_calendar_pre_holiday_cost_capacity_preflight_cli.py`

- [ ] **Step 1: Write failing tests**

```python
result = summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
    factor_frame,
    bars,
    cost_bps_values=(0.0, 20.0),
    portfolio_values=(100000.0,),
    top_n=5,
)
self.assertFalse(result["promotion_policy"]["promotion_allowed"])
self.assertEqual(result["thresholds"]["factor_name"], "pre_holiday_liquidity_avoidance_5_3")
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.unit.test_cn_calendar_pre_holiday_cost_capacity_preflight tests.unit.test_cn_calendar_pre_holiday_cost_capacity_preflight_cli`

Expected: FAIL because the preflight module and CLI do not exist.

### Task 2: Implement Preflight

**Files:**
- Create: `src/quant_robot/ops/cn_calendar_pre_holiday_cost_capacity_preflight.py`
- Create: `scripts/run_cn_calendar_pre_holiday_cost_capacity_preflight.py`

- [ ] **Step 1: Build residual factor frame**

Use Round164 feature/factor/exposure helpers and residualize only `pre_holiday_liquidity_avoidance_5_3`.

- [ ] **Step 2: Run fixed cost/capital stress**

Use fixed TopN, holding, execution lag, cost bps values, portfolio values, max participation, and drawdown floor. Do not tune on results.

- [ ] **Step 3: Gate output**

Allow only `walk_forward_candidate`; keep `promotion_allowed=False` for all cases.

### Task 3: Real Run And Report

**Files:**
- Create: `docs/research/cn_stock_pre_holiday_cost_capacity_preflight_round165_2026-06-23.md`

- [ ] **Step 1: Run real preflight**

Run: `python scripts/run_cn_calendar_pre_holiday_cost_capacity_preflight.py --output-dir data/reports/cn_calendar_pre_holiday_cost_capacity_preflight_round165_20260623`

Expected: structured local output with cost/capacity leaderboard and no promotion.
