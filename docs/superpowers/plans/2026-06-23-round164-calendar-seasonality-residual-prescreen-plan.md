# Round164 Calendar Seasonality Residual Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate the eight frozen Round163 CN-stock calendar-seasonality candidates with a long-cycle residual IC prescreen before any portfolio grid or promotion.

**Architecture:** Add a focused residual prescreen module and CLI following the existing neutral/residual prescreen pattern. The feature frame derives only ex-ante trading-calendar states and lagged price/liquidity features, then applies industry neutralization, style residualization, reference-correlation dedup, calendar-bucket coverage, yearly stability, and 2015 stress reporting.

**Tech Stack:** Python, pandas, numpy, existing residualization helpers, JSON/Markdown/CSV outputs, `unittest`.

---

### Task 1: Tests First

**Files:**
- Create: `tests/unit/test_cn_calendar_seasonality_residual_prescreen.py`
- Create: `tests/unit/test_cn_calendar_seasonality_residual_prescreen_cli.py`

- [ ] **Step 1: Write failing tests**

```python
features = build_cn_calendar_seasonality_feature_frame(bars, horizons=(5,), execution_lag=1)
self.assertIn("ex_ante_turn_of_month_window", features.columns)
self.assertIn("ex_ante_pre_holiday_1_to_3_trading_days", features.columns)
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.unit.test_cn_calendar_seasonality_residual_prescreen tests.unit.test_cn_calendar_seasonality_residual_prescreen_cli`

Expected: FAIL because the residual prescreen module and CLI do not exist yet.

### Task 2: Implement Prescreen

**Files:**
- Create: `src/quant_robot/ops/cn_calendar_seasonality_residual_prescreen.py`
- Create: `scripts/run_cn_calendar_seasonality_residual_prescreen.py`

- [ ] **Step 1: Build feature frame**

Compute returns, forward labels, ADV, volatility, beta, and ex-ante calendar flags from the CN trading date list.

- [ ] **Step 2: Build factor, reference, exposure, and label frames**

Use the eight frozen candidate names from Round163. No new factor names are introduced in Round164.

- [ ] **Step 3: Summarize gates**

Block candidates on weak industry-neutral IC, weak residual IC, yearly instability, 2015 stress failure, low calendar-bucket coverage, high reference redundancy, or high style exposure.

### Task 3: Run And Report

**Files:**
- Create: `docs/research/cn_stock_cn_calendar_seasonality_residual_prescreen_round164_2026-06-23.md`

- [ ] **Step 1: Run long-cycle prescreen**

Run: `python scripts/run_cn_calendar_seasonality_residual_prescreen.py --output-dir data/reports/cn_calendar_seasonality_residual_prescreen_round164_20260623`

Expected: structured local report with zero promotion candidates and next direction determined by residual lead count.

- [ ] **Step 2: Verify**

Run the new tests, compile the module/CLI, and confirm no `data/reports` files are tracked by Git.
