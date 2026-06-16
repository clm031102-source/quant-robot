# Factor Method Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the strongest cloud-mined residualized liquidity-aware probe into a pre-registered, auditable research method without weakening research-to-paper safety boundaries.

**Architecture:** Extend the existing moneyflow technical combo factor family with a multi-exposure residual operation and signal-date amount gate. Add a strict regime-aware walk-forward config so regime lookbacks are tested as explicit hypotheses rather than selected after seeing results. Absorb the latest office desktop evidence into the integration manifest.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot` research pipeline, JSON configs, git sync manifest.

---

### Task 1: Factor Behavior

**Files:**
- Modify: `tests/unit/test_moneyflow_technical_combo_factors.py`
- Modify: `src/quant_robot/factors/moneyflow_technical.py`

- [x] Add tests that `large_resid_liq_vol_amt_20` is registered, residualizes large-order flow against liquidity, volatility, and log amount, and blocks rows below the configured amount floor.
- [x] Run the focused test and confirm it fails before implementation.
- [x] Implement the new factor spec and minimal residual/amount-gate logic.
- [x] Run the focused test and confirm it passes.

### Task 2: Strict Validation Config

**Files:**
- Create: `configs/walk_forward_tushare_moneyflow_residual_regime.json`
- Modify: `scripts/run_project_audit.py` if registry validation needs to recognize the new config.

- [x] Add a config that tests only the residualized liquidity-aware family with explicit regime lookbacks, cost, capacity, relative-return, and drawdown gates.
- [x] Run project audit to confirm the factor registry accepts the new config.

### Task 3: Cloud Evidence Absorption

**Files:**
- Modify: `docs/research/office_desktop_factor_mining_2026-06-16_incremental.md`
- Modify: `configs/factor_branch_integration_manifest.json`

- [x] Absorb commit `c5f520f3d9a666ffef25c905cee4e103d2c8e977` into the research document.
- [x] Record the commit as `absorbed` with a strict-validation-only summary.

### Task 4: Verification And Sync

**Files:**
- No production files beyond Tasks 1-3.

- [x] Run focused unit tests for moneyflow technical factors.
- [x] Run project audit.
- [x] Run laptop check profile or the broad unit suite if feasible.
- [x] Commit and push the task branch.
