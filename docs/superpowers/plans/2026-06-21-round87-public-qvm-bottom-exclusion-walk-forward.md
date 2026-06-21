# Round87 Public QVM Bottom-Exclusion Walk-Forward Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate whether the two frozen Round86 public QVM leads work as bottom-exclusion risk filters under costed rolling walk-forward gates.

**Architecture:** Reuse the existing bottom-exclusion walk-forward path instead of writing a new backtest engine. Feed the Round86 `daily_basic_public_quality_value_momentum` factor source through the experiment-grid precompute helper, then run `scripts/run_bottom_exclusion_walk_forward.py` with fixed parameters and strict train/test folds.

**Tech Stack:** Python, pandas, existing `quant_robot` research pipeline, authority processed CN stock bars, JSON configs, Markdown research reports.

---

### Task 1: Round87 Config And Preregistration

**Files:**
- Create: `configs/experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json`
- Create: `docs/research/cn_stock_public_qvm_bottom_exclusion_preregistration_round87_2026-06-21.md`

- [ ] **Step 1: Create the frozen experiment-grid config**

Use only these two factors:

```json
[
  "public_qvm_value_reversal_quality_20",
  "public_qvm_lowbeta_value_momentum_20"
]
```

Use source `daily_basic_public_quality_value_momentum`, market `CN`, `forward_horizon=20`, `execution_lag=1`, `rebalance_intervals=[10]`, `cost_bps_values=[10.0]`, `market_impact_bps=20.0`, `max_participation_rate=0.01`, `min_signal_amount=10000000`, `portfolio_value=1000000.0`, `target_gross_exposure=0.6`, and `output_dir=data/reports/experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621`.

- [ ] **Step 2: Write preregistration**

Record that this is not parameter tuning. The only question is whether the Round86 QVM signals work as bottom-exclusion filters after costs, capacity, and rolling out-of-sample validation.

- [ ] **Step 3: Validate JSON**

Run:

```powershell
python -m json.tool configs\experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json
```

Expected: valid JSON printed and exit code 0.

### Task 2: Run Costed Bottom-Exclusion Walk-Forward

**Files:**
- Read: `scripts/run_bottom_exclusion_walk_forward.py`
- Generated ignored output: `data/reports/bottom_exclusion_walk_forward_public_qvm_round87_20260621`

- [ ] **Step 1: Run the existing walk-forward entrypoint**

```powershell
python scripts\run_bottom_exclusion_walk_forward.py `
  --grid-config configs\experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json `
  --source authority-processed-bars `
  --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --output-dir data\reports\bottom_exclusion_walk_forward_public_qvm_round87_20260621 `
  --rolling-train-days 756 `
  --rolling-test-days 252 `
  --rolling-step-days 252 `
  --min-accepted-folds 2 `
  --bottom-quantile 0.2 `
  --rebalance-interval 10 `
  --holding-period 20 `
  --cost-bps 10 `
  --market-impact-bps 20 `
  --max-participation-rate 0.01 `
  --min-entry-amount 10000000 `
  --portfolio-value 1000000 `
  --target-gross-exposure 0.6 `
  --min-positive-relative-fold-rate 0.6 `
  --min-test-overlap-adjusted-sharpe 0.5 `
  --max-test-drawdown-limit 0.5
```

Expected: two QVM cases complete across rolling folds and write JSON/CSV/Markdown outputs.

- [ ] **Step 2: Inspect leaderboard**

Read:

```powershell
Get-Content data\reports\bottom_exclusion_walk_forward_public_qvm_round87_20260621\bottom_exclusion_walk_forward.json
Import-Csv data\reports\bottom_exclusion_walk_forward_public_qvm_round87_20260621\walk_forward_leaderboard.csv
```

Record accepted folds, mean test total return, mean test relative return, mean test overlap-adjusted Sharpe, worst test drawdown, win rate, and test capacity-limited trades.

### Task 3: Round87 Report And Startup Gate

**Files:**
- Create: `docs/research/cn_stock_public_qvm_bottom_exclusion_walk_forward_round87_2026-06-21.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`

- [ ] **Step 1: Write the Round87 report**

Include:

- setup and exact command;
- results table for both factors;
- accepted/rejected count;
- reasons for rejection or carry-forward;
- comparison against Round86 direct TopN failure;
- next direction.

- [ ] **Step 2: Update startup gate**

If both factors fail, set next direction to rotate away from QVM. If one passes, set next direction to promotion-gate review before any integration.

### Task 4: Verification

**Files:**
- Test: relevant unit tests for bottom-exclusion walk-forward, project audit, experiment runner, and startup gate

- [ ] **Step 1: Run focused tests**

```powershell
python -m unittest tests.unit.test_bottom_exclusion_walk_forward tests.unit.test_bottom_exclusion_portfolio_backtest tests.unit.test_experiment_runner tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_project_audit
```

Expected: all tests pass.

- [ ] **Step 2: Run project audit**

```powershell
python scripts\run_project_audit.py --json
```

Expected: `summary.passes=true`, `factor_config_registry.passes=true`, and no forbidden hits.

- [ ] **Step 3: Check diff hygiene**

```powershell
git diff --check
```

Expected: no whitespace errors; Windows LF/CRLF warnings are acceptable.
