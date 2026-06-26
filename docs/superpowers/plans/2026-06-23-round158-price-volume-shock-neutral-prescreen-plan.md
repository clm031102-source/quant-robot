# Round158 Price-Volume Shock Neutral Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Round157 price-volume shock candidates through long-cycle raw, industry-neutral, residual IC, and reference-dedup gates before any portfolio grid is allowed.

**Architecture:** Add a focused neutral-prescreen module that builds price-volume shock features from CN daily bars, computes all eight preregistered candidates, neutralizes by industry, residualizes against size/liquidity/volatility/recent-return exposures, checks reference redundancy, and writes structured outputs. The CLI uses existing local CN bar roots and stock-basic metadata.

**Tech Stack:** Python, pandas, numpy, existing factor IC helpers, existing industry neutralization/residualization helpers, `unittest`.

---

### Task 1: Neutral Prescreen Unit Behavior

**Files:**
- Create: `tests/unit/test_price_volume_shock_reversal_neutral_prescreen.py`
- Create: `src/quant_robot/ops/price_volume_shock_reversal_neutral_prescreen.py`

- [ ] **Step 1: Write failing tests**

Require the summary stage, eight candidates, raw/industry/residual result rows, zero promotion permission, multiple-testing accounting, and no portfolio grid before residual/reference gates.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_neutral_prescreen`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement minimal neutral prescreen**

Create feature generation, candidate value computation, industry neutralization, residualization, reference correlation checks, result summaries, and writers.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_neutral_prescreen`

Expected: PASS.

### Task 2: CLI And Real Run

**Files:**
- Create: `tests/unit/test_price_volume_shock_reversal_neutral_prescreen_cli.py`
- Create: `scripts/run_price_volume_shock_reversal_neutral_prescreen.py`
- Create: `docs/research/cn_stock_price_volume_shock_reversal_neutral_prescreen_round158_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Write CLI failing test**

Require output JSON/Markdown/CSV files and summary next direction.

- [ ] **Step 2: Implement CLI**

Use default bars roots, stock-basic metadata, preregistration report, analysis window 2015-01-01 to 2025-12-31, execution lag 1, and final holdout disabled.

- [ ] **Step 3: Run real long-cycle prescreen**

Run the CLI against local processed CN stock data. If runtime is too long, keep the process alive and report progress rather than claiming completion.

- [ ] **Step 4: Update startup gate**

If Round158 completes, set source audit to the Round158 research note and next direction according to the result. If all candidates fail, rotate family instead of parameter-tuning price-volume shock windows.

### Task 3: Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests.unit.test_price_volume_shock_reversal_neutral_prescreen tests.unit.test_price_volume_shock_reversal_neutral_prescreen_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_startup_gate
```

- [ ] **Step 2: Run syntax and JSON checks**

Run:

```powershell
python -m py_compile src\quant_robot\ops\price_volume_shock_reversal_neutral_prescreen.py scripts\run_price_volume_shock_reversal_neutral_prescreen.py
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

- [ ] **Step 3: Keep data out of Git**

Run:

```powershell
git ls-files data/raw data/processed data/reports | Measure-Object | Select-Object -ExpandProperty Count
```
