# 24h Profit Factor Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable 24h factor-mining sprint that prioritizes tradeable, out-of-sample CN stock profit factors before paper-simulation review.

**Architecture:** Keep raw factor mining separate from promotion evidence. Mine only pre-registered economic families, then require full-sample reconstruction, tradeability stress, calendar walk-forward, nested policy selection, and anti-lookahead checks before anything can be called simulation-ready.

**Tech Stack:** Python, pandas, project `quant_robot.ops` diagnostics, unittest, local Tushare-derived CN stock processed data.

---

### Task 1: Sprint Guardrail

**Files:**
- Create: `docs/superpowers/plans/2026-06-27-24h-profit-factor-sprint.md`
- Modify: research notes only when evidence changes

- [x] **Step 1: State the working direction**

Use the current office desktop for CN stock factor validation. The ETF rotation track remains separate. The immediate object is not "any high-return backtest"; it is a signal or portfolio rule that survives tradeability and walk-forward checks.

- [x] **Step 2: Define hard blockers**

Block promotion when any item is true: same-sample-only result, hidden final-holdout tuning, missing cost model, missing tradeability mask, no decision-date alignment, extreme-trade dependence, single-regime win, or parameter choice selected after seeing test results.

### Task 2: Decision-Date Period Returns

**Files:**
- Modify: `src/quant_robot/ops/turnover_low_tradeability_exposure_diagnostic.py`
- Test: `tests/unit/test_turnover_low_tradeability_exposure_diagnostic.py`

- [ ] **Step 1: Write failing test**

Add an assertion that `period_returns[0]` contains `signal_date`, `entry_date`, and `date`, with `date` equal to the exit date. This guards against aligning risk overlays on the exit date by accident.

- [ ] **Step 2: Implement minimal code**

Change the period-return record builder to group the actual trade rows by `exit_date`, aggregate `signal_date` and `entry_date`, and keep the existing return columns.

- [ ] **Step 3: Verify**

Run:

```powershell
python -m unittest tests.unit.test_turnover_low_tradeability_exposure_diagnostic
```

Expected: all tests pass.

### Task 3: Market-State Exposure Cap

**Files:**
- Modify: `src/quant_robot/ops/turnover_low_overlay_walk_forward.py`
- Modify: `scripts/run_turnover_low_overlay_walk_forward.py`
- Test: `tests/unit/test_turnover_low_overlay_walk_forward.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove a market-state policy requires an external cap series, caps exposure on stressed decision dates, and does not use same-period returns to decide exposure.

- [ ] **Step 2: Implement minimal code**

Add `market_state_cap_from_returns`, `align_market_caps_to_returns`, and policy kinds `market_state_cap` and `drawdown_market_state`. Apply caps to the policy exposure before multiplying by period returns.

- [ ] **Step 3: Wire CLI**

Add optional `--market-return-csv`, `--market-return-date-column`, `--market-return-column`, and `--include-market-state-policies` arguments. Keep default behavior unchanged.

- [ ] **Step 4: Verify**

Run:

```powershell
python -m unittest tests.unit.test_turnover_low_overlay_walk_forward tests.unit.test_turnover_low_tradeability_exposure_diagnostic
```

Expected: all tests pass.

### Task 4: Re-run Evidence

**Files:**
- Generated only under `data/reports/`; do not commit generated data.

- [ ] **Step 1: Rebuild tradeability period returns**

Run the turnover-low tradeability exposure diagnostic with the fixed decision-date output.

- [ ] **Step 2: Re-run overlay walk-forward**

Run the overlay CLI with market-state policies and record whether nested selection still beats the drawdown-only overlay.

- [ ] **Step 3: Update research note**

Update the Round316-321 note or create a Round322+ note with exact metrics, blockers, and next direction.

### Task 5: Continue Mining

**Files:**
- New docs/configs/tests only for evidence that passes the above gates.

- [ ] **Step 1: After three rounds, audit direction**

Ask: did the last three rounds test a real hypothesis, did they reduce uncertainty, and should the next round stay in the same factor family?

- [ ] **Step 2: After ten rounds, sync**

Run the repository sync audit, verify no forbidden data paths are staged, commit code/docs only, and push the task branch.
