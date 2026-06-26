# Round156 Public Technical Failure-Reversal Neutral Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the Round155 `inverse_rsrs_slope_failure_liquid_18_60` 5-day lead survives industry, size, liquidity, reference-factor, and residual IC gates before any portfolio grid.

**Architecture:** Add a focused Round156 module that reuses the Round155 lightweight technical feature frame, computes only the one lead and a small reference/exposure pack, then summarizes raw and residual IC. Keep promotion and portfolio conversion blocked unless this audit produces a later preflight candidate.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops.public_technical_failure_reversal_prescreen` and `quant_robot.ops.market_residual_lead_exposure_dedup` helpers.

---

### Task 1: Unit Tests

**Files:**
- Create: `tests/unit/test_public_technical_failure_reversal_neutral_dedup.py`

- [ ] **Step 1: Write failing tests**

Create tests that build synthetic lead, labels, reference factors, and exposure frames. The first test must verify high reference and high exposure correlations block portfolio conversion. The second test must verify a residual signal that survives exposure neutralization can become a portfolio preflight candidate while promotion remains blocked.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.unit.test_public_technical_failure_reversal_neutral_dedup`

Expected: fail with `ModuleNotFoundError` or missing function errors because the Round156 module does not exist yet.

### Task 2: Round156 Module

**Files:**
- Create: `src/quant_robot/ops/public_technical_failure_reversal_neutral_dedup.py`

- [ ] **Step 1: Implement minimal API**

Expose `build_public_technical_failure_reversal_neutral_dedup`, `summarize_public_technical_failure_reversal_neutral_dedup`, `write_public_technical_failure_reversal_neutral_dedup`, and `render_public_technical_failure_reversal_neutral_dedup_markdown`.

- [ ] **Step 2: Compute focused frames**

Use `_technical_feature_frame` and `_candidate_value_series` from Round155 to create one lead factor. Create reference factors for source RSRS positive direction, RSRS residual z, Donchian/efficiency/volume/kbar references, and exposure columns for industry, size, liquidity, volatility, and RSRS ingredients.

- [ ] **Step 3: Gate residual alpha**

Calculate raw IC, residual IC, yearly/monthly IC, reference correlations, exposure correlations, and blockers. Never allow promotion; only allow a later portfolio preflight candidate if no blockers remain.

### Task 3: CLI

**Files:**
- Create: `scripts/run_public_technical_failure_reversal_neutral_dedup.py`

- [ ] **Step 1: Add CLI wrapper**

Mirror the Round155 CLI defaults, read the Round155 prescreen JSON, and write output under `data/reports/public_technical_failure_reversal_neutral_dedup_round156_20260623`.

- [ ] **Step 2: Smoke CLI path in tests if needed**

Keep the CLI importable and return a structured dict for future test extension.

### Task 4: Real Run And Reports

**Files:**
- Create: `docs/research/cn_stock_public_technical_failure_reversal_neutral_dedup_round156_2026-06-23.md`
- Create: `docs/research/cn_stock_round154_156_three_round_review_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Run Round156 on the long-cycle data**

Run the CLI on 2015-01-01 through 2025-12-31, final holdout excluded, horizon 5, execution lag 1.

- [ ] **Step 2: Write research and review reports**

Record raw IC, residual IC, reference/exposure blockers, portfolio-preflight status, promotion status, and the next direction.

- [ ] **Step 3: Update startup gate**

Set `source_audit` to the Round154-156 review or Round156 report and set `next_direction` according to the actual Round156 result.

### Task 5: Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused unit tests**

Run: `python -m unittest tests.unit.test_public_technical_failure_reversal_neutral_dedup tests.unit.test_public_technical_failure_reversal_prescreen tests.unit.test_factor_mining_startup_gate_cli`

- [ ] **Step 2: Compile new Python files**

Run: `python -m py_compile src\quant_robot\ops\public_technical_failure_reversal_neutral_dedup.py scripts\run_public_technical_failure_reversal_neutral_dedup.py`

- [ ] **Step 3: Run startup gate**

Run: `python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\factor_mining_startup_gate_round156_post_review_20260623`

- [ ] **Step 4: Check data files are not tracked**

Run: `git ls-files data/raw data/processed data/reports`
