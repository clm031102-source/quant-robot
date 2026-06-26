# Round112 Market Residual Lead Exposure Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Round112 audit that checks the Round111 market-residual lead for reference-factor redundancy, risk exposure, and 2015/yearly instability before any portfolio grid.

**Architecture:** Add one focused ops module and one CLI script. Reuse existing market-residual factor generation, capacity-safe reference factors, and label helpers. Keep promotion blocked and route the next action to the required three-round review.

**Tech Stack:** Python, pandas, existing `DatasetStore`, existing CN stock factor ops, `unittest`.

---

### File Structure

- Create: `tests/unit/test_market_residual_lead_exposure_dedup.py`
  Unit coverage for summary logic and long-cycle build behavior.
- Create: `tests/unit/test_market_residual_lead_exposure_dedup_cli.py`
  CLI helper coverage for output files.
- Create: `src/quant_robot/ops/market_residual_lead_exposure_dedup.py`
  Round112 audit implementation.
- Create: `scripts/run_market_residual_lead_exposure_dedup.py`
  CLI entrypoint.
- Create: `docs/research/cn_stock_market_residual_lead_exposure_dedup_round112_2026-06-22.md`
  Real run report after verification.
- Modify: `configs/factor_mining_startup_cn_stock.json`
  Advance source audit and next direction after Round112.
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
  Lock the startup gate to the new audit evidence.

### Task 1: RED Tests

- [ ] **Step 1: Write failing summary and build tests**

Create `tests/unit/test_market_residual_lead_exposure_dedup.py` with tests that import:

```python
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    build_market_residual_lead_exposure_dedup,
    summarize_market_residual_lead_exposure_dedup,
)
```

The summary test must create synthetic 2015 negative IC and 2016 positive IC, a duplicate reference factor, and high beta exposure. Expected blockers:

```python
"lead_highly_redundant_with_reference_factor"
"twenty_fifteen_regime_failure_unexplained"
"yearly_ic_instability"
"lead_high_exposure_to_market_or_liquidity_proxy"
```

- [ ] **Step 2: Write failing CLI test**

Create `tests/unit/test_market_residual_lead_exposure_dedup_cli.py` importing:

```python
from scripts.run_market_residual_lead_exposure_dedup import run_market_residual_lead_exposure_dedup_cli
```

Assert JSON, Markdown, reference correlation CSV, exposure correlation CSV, yearly IC CSV, monthly IC CSV, and IC observation CSV are written.

- [ ] **Step 3: Run RED**

Run:

```powershell
python -m unittest tests.unit.test_market_residual_lead_exposure_dedup tests.unit.test_market_residual_lead_exposure_dedup_cli
```

Expected: import failures for missing module and script.

### Task 2: GREEN Implementation

- [ ] **Step 1: Implement the ops module**

Create `src/quant_robot/ops/market_residual_lead_exposure_dedup.py` with:

```python
def build_market_residual_lead_exposure_dedup(...): ...
def summarize_market_residual_lead_exposure_dedup(...): ...
def write_market_residual_lead_exposure_dedup(...): ...
def render_market_residual_lead_exposure_dedup_markdown(...): ...
```

The module must compute:

- daily lead IC observations;
- yearly IC;
- monthly IC;
- lead/reference daily Spearman correlations;
- lead/exposure daily Spearman correlations;
- blockers and next direction.

- [ ] **Step 2: Implement CLI**

Create `scripts/run_market_residual_lead_exposure_dedup.py` with `run_market_residual_lead_exposure_dedup_cli` and `main`.

- [ ] **Step 3: Run GREEN unit tests**

Run:

```powershell
python -m unittest tests.unit.test_market_residual_lead_exposure_dedup tests.unit.test_market_residual_lead_exposure_dedup_cli
```

Expected: all Round112 tests pass.

### Task 3: Real Long-Cycle Round112 Run

- [ ] **Step 1: Run the real audit**

Run:

```powershell
python scripts\run_market_residual_lead_exposure_dedup.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --prescreen-report data\reports\market_residual_risk_premia_prescreen_round111_20260622\market_residual_risk_premia_prescreen.json --output-dir data\reports\market_residual_lead_exposure_dedup_round112_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 20 --execution-lag 1 --sample-every-n-dates 5 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

- [ ] **Step 2: Write the research report**

Create `docs/research/cn_stock_market_residual_lead_exposure_dedup_round112_2026-06-22.md` summarizing the real output and the next action.

### Task 4: Startup Gate Update

- [ ] **Step 1: Update config and test**

Modify `configs/factor_mining_startup_cn_stock.json` and `tests/unit/test_factor_mining_startup_gate_cli.py` so the startup gate reads the Round112 audit and routes to `round113_round110_112_three_round_review_before_next_action`.

- [ ] **Step 2: Run startup gate test**

Run:

```powershell
python -m unittest tests.unit.test_factor_mining_startup_gate_cli
```

Expected: pass.

### Task 5: Verification

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m unittest tests.unit.test_market_residual_lead_exposure_dedup tests.unit.test_market_residual_lead_exposure_dedup_cli tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] **Step 2: Compile new Python files**

Run:

```powershell
python -m py_compile src\quant_robot\ops\market_residual_lead_exposure_dedup.py scripts\run_market_residual_lead_exposure_dedup.py
```

- [ ] **Step 3: Run startup gate**

Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --market CN --asset-type stock --confirm-start --output-dir data\reports\startup_gate_round113_20260622
```

- [ ] **Step 4: Run project audit**

Run:

```powershell
python scripts\run_project_audit.py --json
```

- [ ] **Step 5: Check whitespace and ignored reports**

Run:

```powershell
git diff --check
git status --short --ignored data\reports\market_residual_lead_exposure_dedup_round112_20260622 data\reports\startup_gate_round113_20260622
```

Expected: report directories remain ignored.

### Commit Policy

Do not commit or push during this plan execution. The startup context says `commits_allowed=false` and `pushes_allowed=false`.
