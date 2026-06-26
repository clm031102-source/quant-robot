# Round109 Overnight-Intraday Gap Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a CN stock long-cycle prescreen for pre-registered overnight/intraday gap factors after Round108 forced family rotation.

**Architecture:** Add one focused ops module and one CLI wrapper, reusing the existing capacity-safe bar loader and prescreen summarizer so the evaluation metrics stay consistent with prior rounds. The new module owns candidate definitions and OHLC feature construction only.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops.capacity_safe_price_volume_prescreen` utilities.

---

### Task 1: Add Unit Tests For Candidate Specs And Factor Computation

**Files:**
- Create: `tests/unit/test_overnight_intraday_gap_prescreen.py`

- [ ] **Step 1: Write the failing test**

Create tests that import `default_overnight_intraday_gap_candidate_specs`, `compute_overnight_intraday_gap_factors`, and `summarize_overnight_intraday_gap_prescreen`. Use synthetic OHLCV data with 50 assets and 80 business days. Assert that 10 unique pre-registered factor names are produced, all rows pass amount and ADV20 filters, no promotion is allowed, and a synthetic perfect signal can become a research lead through the summarizer.

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_overnight_intraday_gap_prescreen
```

Expected: fail with `ModuleNotFoundError: No module named 'quant_robot.ops.overnight_intraday_gap_prescreen'`.

### Task 2: Add Unit Tests For CLI

**Files:**
- Create: `tests/unit/test_overnight_intraday_gap_prescreen_cli.py`

- [ ] **Step 1: Write the failing test**

Create a temporary `DatasetStore`, write 2025 and 2026 CN stock bars, run `run_overnight_intraday_gap_prescreen_cli`, and assert the output directory contains JSON, Markdown, candidate CSV, result CSV, and IC observation CSV. Assert the holdout policy excludes 2026 when `include_final_holdout=False`.

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_overnight_intraday_gap_prescreen_cli
```

Expected: fail with `ModuleNotFoundError: No module named 'scripts.run_overnight_intraday_gap_prescreen'`.

### Task 3: Implement Ops Module

**Files:**
- Create: `src/quant_robot/ops/overnight_intraday_gap_prescreen.py`

- [ ] **Step 1: Implement dataclass specs**

Define `OvernightIntradayGapCandidateSpec` with `factor_name`, `family`, `formula_template`, `direction`, `windows`, `required_fields`, `economic_rationale`, and `public_reference_tags`.

- [ ] **Step 2: Implement feature construction**

Use sorted bars by `asset_id,date`; compute `prev_close`, `overnight_return = open / prev_close - 1`, `intraday_return = adj_close / open - 1`, `return_1d`, `realized_vol_20`, `adv20_amount`, gap-fill terms, rolling sums/means, and cross-sectional z-scores.

- [ ] **Step 3: Implement factor generation**

Generate the ten registered factor names only, apply capacity mask, and return columns `date`, `asset_id`, `market`, `factor_name`, `factor_value`, `amount`, `adv20_amount`.

- [ ] **Step 4: Implement build/write/render functions**

Reuse `load_capacity_safe_bars`, `make_forward_returns`, and `summarize_capacity_safe_price_volume_prescreen`. Write JSON/Markdown/CSV artifacts with stage-specific filenames.

### Task 4: Implement CLI

**Files:**
- Create: `scripts/run_overnight_intraday_gap_prescreen.py`

- [ ] **Step 1: Add CLI wrapper**

Expose `run_overnight_intraday_gap_prescreen_cli` and `main()` with defaults for the two local CN stock data roots, horizons `5,20`, execution lag `1`, and output directory `data/reports/overnight_intraday_gap_prescreen`.

- [ ] **Step 2: Print concise JSON summary**

Print `summary`, `data_window`, `next_direction`, and `output_dir`.

### Task 5: Verify And Run Real Round109

**Files:**
- Create: `docs/research/cn_stock_overnight_intraday_gap_prescreen_round109_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Run unit tests**

```powershell
python -m unittest tests.unit.test_overnight_intraday_gap_prescreen tests.unit.test_overnight_intraday_gap_prescreen_cli
```

- [ ] **Step 2: Run real prescreen**

```powershell
python scripts\run_overnight_intraday_gap_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\overnight_intraday_gap_prescreen_round109_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

- [ ] **Step 3: Write research report and update startup gate**

Record candidate count, test count, research lead count, best factor rows, blockers, and the next direction. Update the startup gate source audit to the Round109 report.

- [ ] **Step 4: Final verification**

```powershell
python -m unittest tests.unit.test_overnight_intraday_gap_prescreen tests.unit.test_overnight_intraday_gap_prescreen_cli tests.unit.test_factor_mining_startup_gate_cli
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --market CN --asset-type stock --confirm-start --output-dir data\reports\startup_gate_round109_20260622
python -m py_compile src\quant_robot\ops\overnight_intraday_gap_prescreen.py scripts\run_overnight_intraday_gap_prescreen.py
python scripts\run_project_audit.py --json
git diff --check
```

Expected: tests pass, startup gate clears, project audit passes, and `git diff --check` has no errors except acceptable Windows line-ending warnings.
