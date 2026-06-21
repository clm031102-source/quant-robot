# Round58 Public Formula Neutral Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the next CN stock factor-mining round on public formula price-volume factors, with industry-neutral IC as the first hard gate and without repeating failed risk-filter-bridge expansion.

**Architecture:** Use the existing `public_formula_price_volume` factor source and existing industry-neutral IC tooling. Create a dedicated Round58 config that can feed direct grid, neutral IC, and optional portfolio checks; run the neutral IC audit first so weak or industry-dominated factors are rejected before expensive portfolio runs.

**Tech Stack:** Python, pandas, existing experiment grid runner, `scripts/run_industry_neutral_ic_audit.py`, `scripts/run_industry_neutral_portfolio_backtest.py`, `unittest`.

---

### Task 1: Register Round58 Config

**Files:**
- Create: `configs/experiment_grid_cn_stock_public_formula_price_volume_round58_20260621.json`

- [ ] **Step 1: Create a config with all public formula price-volume factors**

Use factor source `public_formula_price_volume` and these registered factor names:

```json
[
  "formula_pv_corr_reversal_20",
  "formula_volume_contraction_reversal_20",
  "formula_range_contraction_breakout_20",
  "formula_range_contraction_breakout_liquid_20",
  "formula_range_contraction_breakout_lowvol_20",
  "formula_range_contraction_breakout_liquid_lowvol_20",
  "formula_pv_corr_momentum_confirmed_20_60",
  "formula_volume_contraction_momentum_confirmed_20_60"
]
```

- [ ] **Step 2: Verify config registry**

Run:

```powershell
python scripts\run_project_audit.py --json
```

Expected: `"passes": true`, no unknown factor refs, no unsupported factor sources.

### Task 2: Run Industry-Neutral IC Gate First

**Files:**
- Output: `data/reports/industry_neutral_ic_audit_public_formula_price_volume_round58_20260621`

- [ ] **Step 1: Run neutral IC audit**

Run:

```powershell
python scripts\run_industry_neutral_ic_audit.py --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_round58_20260621.json --source authority-processed-bars --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\industry_neutral_ic_audit_public_formula_price_volume_round58_20260621
```

Expected: JSON summary prints `industry_neutral_signal_factors`, `industry_exposure_dominated_factors`, and recommended next actions.

- [ ] **Step 2: Branch on the result**

If `industry_neutral_signal_factors` is `0`, stop this family and write a rejection report.

If `industry_neutral_signal_factors` is greater than `0`, run industry-neutral portfolio next.

### Task 3: Conditional Industry-Neutral Portfolio

**Files:**
- Output: `data/reports/industry_neutral_portfolio_public_formula_price_volume_round58_20260621`

- [ ] **Step 1: Run only when neutral IC survives**

Run:

```powershell
python scripts\run_industry_neutral_portfolio_backtest.py --config configs\experiment_grid_cn_stock_public_formula_price_volume_round58_20260621.json --source authority-processed-bars --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\industry_neutral_portfolio_public_formula_price_volume_round58_20260621
```

Expected: completed cases with `selection_method=industry_neutral_top_n`.

### Task 4: Report And Direction Decision

**Files:**
- Create: `docs/research/cn_stock_public_formula_price_volume_round58_2026-06-21.md`
- Modify if direction changes: `configs/factor_mining_startup_cn_stock.json`
- Test: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Write the Round58 report**

Record:

- neutral IC classification counts;
- factor names that survive or fail;
- whether portfolio was run;
- promotable, paper-ready, research-lead, and rejected counts;
- whether the family should continue.

- [ ] **Step 2: Update startup direction**

If the family fails neutral IC, rotate away from public formula price-volume.

If one or more neutral factors survive but portfolio fails, set the next direction to portfolio construction or bottom-exclusion diagnostic for only the survivors.

### Verification

- [ ] `python -m unittest tests.unit.test_industry_neutral_ic_audit tests.unit.test_project_audit.ProjectAuditTests.test_audit_accepts_registered_public_formula_price_volume_factor_source tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_is_runnable`
- [ ] `python scripts\run_project_audit.py --json`
- [ ] `python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start`
