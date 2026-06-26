# Round111 Market Residual Risk Premia Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a long-cycle prescreen for the 10 Round110 market-residual risk-premia candidates.

**Architecture:** Reuse the existing capacity-safe prescreen loader, label builder, statistical summarizer, and report-writing conventions. Add a focused market-residual feature builder that creates an equal-weight market proxy, rolling beta/residual features, candidate scores, and Round111-specific output metadata.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops` and `quant_robot.research.labels` modules.

---

### Task 1: Tests First

**Files:**
- Create: `tests/unit/test_market_residual_risk_premia_prescreen.py`
- Create: `tests/unit/test_market_residual_risk_premia_prescreen_cli.py`

- [ ] **Step 1: Write unit tests for same-date market proxy and prescreen policy**

Tests must import `build_equal_weight_market_proxy`, `compute_market_residual_risk_premia_factors`, and `build_market_residual_risk_premia_prescreen`.

- [ ] **Step 2: Write CLI test**

The CLI test must write synthetic CN stock bars to a temporary `DatasetStore`, run the script wrapper, and assert JSON, Markdown, results CSV, candidates CSV, and IC CSV are created.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.unit.test_market_residual_risk_premia_prescreen tests.unit.test_market_residual_risk_premia_prescreen_cli
```

Expected: fail because the Round111 module and script do not exist yet.

### Task 2: Prescreen Module

**Files:**
- Create: `src/quant_robot/ops/market_residual_risk_premia_prescreen.py`

- [ ] **Step 1: Implement `build_equal_weight_market_proxy`**

It must compute daily stock returns per asset and then same-date equal-weight market return from finite eligible rows.

- [ ] **Step 2: Implement feature matrix construction**

It must compute rolling beta, downside beta, market correlation, residual returns, residual volatility, downside residual volatility, residual momentum, residual efficiency, co-crash counts, residual skew, beta-adjusted range, and cross-sectional z-scores by date.

- [ ] **Step 3: Implement candidate scores**

It must materialize exactly the 10 Round110 registered candidate names by default.

- [ ] **Step 4: Implement build, summarize wrapper, write, and Markdown renderer**

Reuse the existing capacity-safe prescreen summary metrics, but override stage, promotion policy, public reference review, and market-residual diagnostics.

### Task 3: CLI Script

**Files:**
- Create: `scripts/run_market_residual_risk_premia_prescreen.py`

- [ ] **Step 1: Add wrapper function**

Expose `run_market_residual_risk_premia_prescreen_cli` for tests and scripts.

- [ ] **Step 2: Add argparse entrypoint**

Support `--bars-root`, `--output-dir`, `--analysis-start-date`, `--analysis-end-date`, `--include-final-holdout`, `--horizons`, `--execution-lag`, `--min-cross-section`, `--min-ic-observations`, and `--min-signal-date-amount`.

### Task 4: Verification And Real Run

- [ ] **Step 1: Run focused unit tests**

```powershell
python -m unittest tests.unit.test_market_residual_risk_premia_prescreen tests.unit.test_market_residual_risk_premia_prescreen_cli
```

- [ ] **Step 2: Run Round111 real prescreen**

```powershell
python scripts\run_market_residual_risk_premia_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\market_residual_risk_premia_prescreen_round111_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

- [ ] **Step 3: Write Round111 research report**

Create `docs/research/cn_stock_market_residual_risk_premia_prescreen_round111_2026-06-22.md` with candidate counts, lead counts, best metrics, blockers, and next direction.

- [ ] **Step 4: Update startup gate**

Move `next_direction` according to evidence:

- if leads survive: `round112_market_residual_lead_exposure_dedup`
- if no leads survive: `round112_family_rotation_after_market_residual_prescreen_failure`

- [ ] **Step 5: Verify project gates**

Run unit tests, JSON parse, py_compile, startup gate, project audit, and diff check.

