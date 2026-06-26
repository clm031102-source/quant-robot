# Round160 CN Tradeability Limit Event Proxy Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Round159 tradeability/limit-event candidates through a long-cycle proxy IC, industry-neutral, style-residual, and tradeability-blocked signal screen before any portfolio grid is considered.

**Architecture:** Add a focused proxy-prescreen module that loads CN daily bars, builds board-aware limit-event proxy features from current and lagged daily OHLCV data, computes all Round159 candidates, and reuses existing IC/neutralization/residualization helpers. The output remains research-only because official true limit/suspension feeds are not yet audited.

**Tech Stack:** Python, pandas, numpy, existing CN bar loader, existing IC and residualization helpers, `unittest`.

---

### Task 1: Proxy Feature And Prescreen Behavior

**Files:**
- Create: `tests/unit/test_cn_tradeability_limit_event_proxy_prescreen.py`
- Create: `src/quant_robot/ops/cn_tradeability_limit_event_proxy_prescreen.py`

- [ ] **Step 1: Write failing tests**

Require current/lagged limit-down relief features without next-day signal inputs, all eight Round159 candidates, tradeability-blocked signal accounting, residual IC output, and no promotion or portfolio permission.

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests.unit.test_cn_tradeability_limit_event_proxy_prescreen`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement minimal proxy prescreen**

Create feature generation, candidate value computation, industry neutralization, residualization, reference/exposure checks, result summaries, and writers.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m unittest tests.unit.test_cn_tradeability_limit_event_proxy_prescreen`

Expected: PASS.

### Task 2: CLI And Real Run

**Files:**
- Create: `tests/unit/test_cn_tradeability_limit_event_proxy_prescreen_cli.py`
- Create: `scripts/run_cn_tradeability_limit_event_proxy_prescreen.py`
- Create: `docs/research/cn_stock_cn_tradeability_limit_event_proxy_prescreen_round160_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Write CLI failing test**

Require JSON/Markdown/CSV outputs and a summary that explicitly blocks promotion while true limit status remains proxy-only.

- [ ] **Step 2: Implement CLI**

Use default long-cycle CN stock bar roots, stock-basic metadata, Round159 preregistration output, execution lag 1, horizon 5, and final holdout disabled.

- [ ] **Step 3: Run real long-cycle proxy prescreen**

Run the CLI against local processed CN stock data. If runtime is long, keep it running and report progress instead of claiming completion.

- [ ] **Step 4: Update startup gate**

Set the next direction according to results: if zero residual proxy leads survive, rotate family; if leads survive, require true-limit status audit and cost/capacity preflight before any portfolio grid.

### Task 3: Verification And Round160 Sync Decision

**Files:**
- All files above.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests.unit.test_cn_tradeability_limit_event_proxy_prescreen tests.unit.test_cn_tradeability_limit_event_proxy_prescreen_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_startup_gate
```

- [ ] **Step 2: Run syntax and JSON checks**

Run:

```powershell
python -m py_compile src\quant_robot\ops\cn_tradeability_limit_event_proxy_prescreen.py scripts\run_cn_tradeability_limit_event_proxy_prescreen.py
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

- [ ] **Step 3: Keep data out of Git**

Run:

```powershell
git ls-files data/raw data/processed data/reports | Measure-Object | Select-Object -ExpandProperty Count
```
