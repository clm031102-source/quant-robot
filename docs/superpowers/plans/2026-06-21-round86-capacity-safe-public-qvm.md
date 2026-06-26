# Round86 Capacity-Safe Public QVM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and evaluate a small pre-registered CN stock factor family built from public value, quality/low-volatility, and momentum anomalies with capacity-safe selection gates.

**Architecture:** Implement a new factor source under `src/quant_robot/factors/` so the experiment grid can reuse the existing research pipeline, backtest gates, leaderboards, and decision rules. The factor family should rank only tradeable names inside size buckets, then Round86 should run long-cycle same-parameter replay before any promotion claim.

**Tech Stack:** Python, pandas, unittest, existing `ExperimentGridConfig`, existing authority bars/daily-basic inputs.

---

### Task 1: Add Capacity-Safe QVM Factor Source

**Files:**
- Create: `src/quant_robot/factors/daily_basic_public_quality_value_momentum.py`
- Create: `tests/unit/test_daily_basic_public_quality_value_momentum_factors.py`

- [ ] **Step 1: Write the failing test**

Create tests that import `compute_daily_basic_public_quality_value_momentum_factors`, request three factors, and assert:
- schema columns match `FACTOR_COLUMNS`;
- winners with better value, momentum, low-volatility, and liquidity receive higher scores than weaker peers in the same size bucket;
- low-liquidity names are filtered to `NaN`;
- unknown factor names raise `ValueError`.

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
python -m unittest tests.unit.test_daily_basic_public_quality_value_momentum_factors
```

Expected: failure because the module does not exist.

- [ ] **Step 3: Write minimal implementation**

Add a factor module with these pre-registered names:
- `public_qvm_value_momentum_lowvol_20`
- `public_qvm_dividend_quality_momentum_20`
- `public_qvm_value_reversal_quality_20`
- `public_qvm_lowbeta_value_momentum_20`

Each factor must use only same-day or trailing data, apply a tradeability gate, and output size-bucket percentile ranks.

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
python -m unittest tests.unit.test_daily_basic_public_quality_value_momentum_factors
```

Expected: OK.

### Task 2: Wire Factor Source Into Research Pipeline

**Files:**
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `tests/unit/test_experiment_runner.py`
- Modify: `tests/unit/test_research_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting `factor_source="daily_basic_public_quality_value_momentum"` calls the new builder with `bars`, `daily_basic_inputs`, and requested factor names.

- [ ] **Step 2: Run targeted tests to verify failure**

Run:
```powershell
python -m unittest tests.unit.test_research_pipeline tests.unit.test_experiment_runner
```

Expected: failure because the factor source is not wired.

- [ ] **Step 3: Wire imports and source dispatch**

Import the new compute function and add branches in both pipeline and experiment runner.

- [ ] **Step 4: Run targeted tests to verify pass**

Run:
```powershell
python -m unittest tests.unit.test_daily_basic_public_quality_value_momentum_factors tests.unit.test_research_pipeline tests.unit.test_experiment_runner
```

Expected: OK.

### Task 3: Pre-Register And Run Round86 Long-Cycle Replay

**Files:**
- Create: `configs/experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621.json`
- Create: `docs/research/cn_stock_public_qvm_preregistration_round86_2026-06-21.md`

- [ ] **Step 1: Write config**

Use:
- market `CN`;
- factor source `daily_basic_public_quality_value_momentum`;
- four pre-registered factor names;
- 2015-01-05 to 2025-12-31;
- TopN 100;
- 10 bps cost;
- 20 bps impact;
- 1% ADV capacity;
- signal-date amount gate 10,000,000;
- max calendar holding 60 days;
- factor input root `configs/cn_stock_authority_daily_basic_inputs_2015_2025.json`.

- [ ] **Step 2: Run startup gate**

Run:
```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start
```

Expected: `startup_gate_cleared: true` and next direction `round86_capacity_safe_public_quality_value_momentum_composite`.

- [ ] **Step 3: Run experiment grid**

Run:
```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest
```

Expected: completed leaderboard under `data/reports/experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621`.

### Task 4: Audit, Report, And Gate Next Direction

**Files:**
- Create: `docs/research/cn_stock_public_qvm_capacity_safe_round86_2026-06-21.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Analyze leaderboard**

Record total return, annual return, Sharpe, overlap-adjusted Sharpe, max drawdown, win rate, RankIC, RankIC t, relative return, capacity/calendar filtered trades, and decision status.

- [ ] **Step 2: Write report**

Summarize whether any factor is promotable, paper-ready, research-only, or rejected. Explain failure modes and next direction.

- [ ] **Step 3: Update startup gate**

Set `source_audit` to the Round86 report and update `next_direction` based on evidence. Add rejected directions and confirmations.

- [ ] **Step 4: Run verification**

Run:
```powershell
python -m unittest tests.unit.test_daily_basic_public_quality_value_momentum_factors tests.unit.test_research_pipeline tests.unit.test_experiment_runner tests.unit.test_factor_mining_startup_gate_cli
python scripts\run_project_audit.py --json
git diff --check
```

Expected: tests OK, project audit passes, no diff whitespace errors.
