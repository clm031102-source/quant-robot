# Round246 Accounting Quality Statement Event Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PIT-safe accounting-quality event-drift prescreen mode that tests whether cash-conversion improvement with muted announcement reaction predicts post-statement forward returns.

**Architecture:** Reuse the existing accounting-quality statement factor matrix, market context attachment, labels, neutralization, and reporting stack. Add one deliberately simple event-drift candidate so this round changes family logic instead of adding more raw accounting formula tuning.

**Tech Stack:** Python, pandas, existing `quant_robot.ops.accounting_quality_statement_residual_ic_shape_prescreen`, `pytest`, local Tushare processed CN stock data.

---

### Task 1: Red Tests For Event-Drift Mode

**Files:**
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py`

- [x] **Step 1: Add helper-level event-drift test**

Create a small frame with `earnings_cash_conversion_improvement_yoy_raw`, two assets on the same signal date, and bars that allow a pre-announcement close and signal-date close. Assert that the new helper returns exactly `aq_cash_conversion_muted_reaction_drift`, keeps `signal_date > ann_date`, and produces finite factor values.

- [x] **Step 2: Add build-mode test**

Call `build_accounting_quality_statement_residual_ic_shape_prescreen(..., factor_mode="statement_event_drift")` on the existing synthetic statement/bars fixtures. Assert candidate count is `1`, source family is `accounting_quality_statement_event_drift`, and promotion remains blocked.

- [x] **Step 3: Add CLI test**

Call `run_accounting_quality_statement_residual_ic_shape_prescreen_cli(..., factor_mode="statement_event_drift")` and assert the same candidate count plus output CSV creation.

- [x] **Step 4: Run tests and observe RED**

Run:

```powershell
python -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py -q
```

Expected: failures because the helper and mode do not exist yet.

### Task 2: Implement Minimal Event-Drift Candidate

**Files:**
- Modify: `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- Modify: `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

- [x] **Step 1: Add constants and candidate specs**

Add one candidate:

```python
STATEMENT_EVENT_DRIFT_SOURCE_FACTOR_NAME = "earnings_cash_conversion_improvement_yoy_raw"
STATEMENT_EVENT_DRIFT_FACTOR_NAME = "aq_cash_conversion_muted_reaction_drift"
```

The formula is a within-date rank blend of cash-conversion improvement and low absolute announcement reaction.

- [x] **Step 2: Add PIT-safe helper**

Implement `build_accounting_quality_statement_event_drift_factor_frame(frame, bars)`. It must only use rows where `signal_date > ann_date`, compute reaction from the last close before `ann_date` to the close at or before `signal_date`, and set the factor date to the existing signal date so labels still enter after `execution_lag=1`.

- [x] **Step 3: Wire build mode and CLI choice**

Accept `factor_mode="statement_event_drift"` in the builder and CLI. Set `candidate_family` to `accounting_quality_statement_event_drift` and keep promotion blocked.

- [x] **Step 4: Run tests and observe GREEN**

Run:

```powershell
python -m pytest tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen.py tests\unit\test_accounting_quality_statement_residual_ic_shape_prescreen_cli.py -q
```

Expected: all accounting-quality residual IC tests pass.

### Task 3: Run Round246 130-Symbol Prescreen

**Files:**
- Create: `configs/accounting_quality_statement_event_drift_round246_20260625.json`
- Create: `docs/research/cn_stock_round246_accounting_quality_statement_event_drift_2026-06-25.md`

- [x] **Step 1: Execute the full local 130-symbol run**

Run the new mode over the accumulated statement shards, existing bars roots, daily-basic context, and stock-basic metadata. Output under `data/reports/round246_accounting_quality_statement_event_drift_residual_ic_130_symbol_20260625`.

- [x] **Step 2: Summarize exact results**

Extract candidate count, factor rows, aligned rows, IC, ICIR, t-stat, FDR, neutral ICs, research lead count, and promotion allowance.

- [x] **Step 3: Write config and research report**

Document the hypothesis, PIT controls, sample window, exact command, output path, results, failure reasons if any, and next direction.

### Task 4: Verification And Closeout

**Files:**
- Verify all modified code/tests/config/docs.

- [x] **Step 1: Validate JSON**

Run JSON parsing on the new config.

- [x] **Step 2: Run focused tests**

Run the accounting-quality formula, matrix-label, residual IC, and CLI unit tests touched by this round.

- [x] **Step 3: Check report extraction, whitespace, and running Python processes**

Confirm the output summary is readable, no trailing whitespace exists in touched files, and no stray Python mining process remains.

- [x] **Step 4: Update this plan checklist**

Mark all completed steps and report remaining gaps honestly.
