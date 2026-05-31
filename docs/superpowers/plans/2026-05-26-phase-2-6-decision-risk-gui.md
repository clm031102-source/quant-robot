# Phase 2.6 Decision Risk And GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a research-only decision risk layer with benchmark comparison, regime gating, and drawdown guards, then replace the local GUI with a readable operational console.

**Architecture:** Keep decision logic in a new research module and call it from the existing research pipeline, experiment grid, walk-forward validation, and paper simulator. Keep GUI changes in the static frontend and demo service, using the same local JSON APIs and no live trading or broker concepts.

**Tech Stack:** Python 3.11, pandas, standard-library unittest, plain HTML/CSS/JavaScript served by the existing local HTTP app.

---

## File Structure

- Create `src/quant_robot/research/decision.py`: benchmark curves, cash comparison, regime filter, and decision pass/fail helpers.
- Modify `src/quant_robot/research/pipeline.py`: apply optional regime filter and attach decision metrics.
- Modify `src/quant_robot/experiments/runner.py`: surface decision metrics in grid rows and allow ranking/filtering by them.
- Modify `src/quant_robot/validation/walk_forward.py`: reject candidates by drawdown and relative benchmark thresholds.
- Modify `src/quant_robot/paper/simulator.py`: add optional drawdown guard and expose guard events.
- Modify `scripts/run_research_pipeline.py`, `scripts/run_paper_simulation.py`: expose conservative CLI flags.
- Modify `configs/experiment_grid_cn_etf_low_turnover.json`, `configs/walk_forward_cn_etf_low_turnover.json`: add 2.6 defaults.
- Create `docs/phase_2_6_decision_risk.md`: document the research-only decision layer.
- Modify `README.md`, `docs/cn_etf_real_csv_report.md`: point the next research path at 2.6.
- Modify `src/quant_robot/gui/research_service.py`, `src/quant_robot/gui/app.py`, `src/quant_robot/gui/static/index.html`, `src/quant_robot/gui/static/app.js`, `src/quant_robot/gui/static/styles.css`: readable GUI and 2.6 metrics.
- Test `tests/unit/test_decision_risk.py`, `tests/unit/test_research_pipeline.py`, `tests/unit/test_experiment_runner.py`, `tests/unit/test_walk_forward.py`, `tests/unit/test_paper_simulation.py`, `tests/unit/test_gui.py`.

## Task 1: Decision Risk Core

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_decision_risk.py` with tests for equal-weight benchmark curves, benchmark asset curves, cash comparison, regime blocking, and decision pass/fail summaries.

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_decision_risk
```

Expected: import failure for `quant_robot.research.decision`.

- [ ] **Step 3: Implement core module**

Implement deterministic pandas helpers:

```python
def build_benchmark_curve(bars, benchmark_asset_id=None):
    ...

def compare_strategy_to_benchmark(equity_curve, benchmark_curve, cash_annual_return=0.0, periods_per_year=252.0):
    ...

def regime_allowed_dates(bars, benchmark_asset_id=None, lookback=20, require_positive_momentum=True):
    ...

def decision_summary(metrics, min_relative_return=0.0, max_drawdown_limit=None):
    ...
```

- [ ] **Step 4: Verify green**

Run the same focused test. Expected: pass.

## Task 2: Research Pipeline Integration

- [ ] **Step 1: Write failing tests**

Extend `tests/unit/test_research_pipeline.py` so a regime filter reduces trades on a falling benchmark and the result includes `decision` and `benchmark_metrics`.

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_research_pipeline
```

Expected: missing config fields or missing `decision`.

- [ ] **Step 3: Implement pipeline fields**

Add optional config fields for `benchmark_asset_id`, `cash_annual_return`, `regime_filter`, `regime_lookback`, `min_relative_return`, and `max_drawdown_limit`. Filter selected signal dates when regime gating is enabled and attach decision metrics.

- [ ] **Step 4: Verify green**

Run the same focused test. Expected: pass.

## Task 3: Grid And Walk-Forward Gates

- [ ] **Step 1: Write failing tests**

Extend experiment and walk-forward tests to assert `relative_return`, `benchmark_total_return`, `decision_status`, and rejection reasons such as `relative_return_below_threshold` and `drawdown_above_limit`.

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_experiment_runner tests.unit.test_walk_forward
```

Expected: missing fields or missing rejection reasons.

- [ ] **Step 3: Implement row propagation and thresholds**

Propagate decision metrics from research results into grid rows. Add walk-forward config fields for minimum relative return and maximum test drawdown.

- [ ] **Step 4: Verify green**

Run the same focused tests. Expected: pass.

## Task 4: Paper Drawdown Guard

- [ ] **Step 1: Write failing tests**

Extend `tests/unit/test_paper_simulation.py` to assert that a configured drawdown guard blocks new buys after the equity curve breaches the limit and records guard events.

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_paper_simulation
```

Expected: missing config fields or no `guard_events`.

- [ ] **Step 3: Implement guard**

Add `max_drawdown_guard` and `guard_cooldown_periods` to paper config. Track peak equity, guarded state, guard events, and skip new buy intents while guarded.

- [ ] **Step 4: Verify green**

Run the same focused test. Expected: pass.

## Task 5: CLI, Config, And Docs

- [ ] **Step 1: Write or extend CLI/config tests**

Add tests only where behavior changes are executable; docs/config changes are verified through full checks.

- [ ] **Step 2: Implement flags and defaults**

Expose 2.6 options in research and paper scripts. Add conservative defaults to low-turnover ETF configs without forcing fixture demos to reject every case.

- [ ] **Step 3: Update docs**

Document commands, output fields, rejection reasons, and the no-live-trading boundary.

- [ ] **Step 4: Verify focused commands**

Run research, grid, walk-forward, and paper fixture commands. Expected: all complete locally.

## Task 6: GUI Rebuild

- [ ] **Step 1: Write failing GUI tests**

Update `tests/unit/test_gui.py` to expect readable Chinese labels, `/api/research/demo` decision metrics, and no mojibake text.

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_gui
```

Expected: current static files contain unreadable labels and miss 2.6 metrics.

- [ ] **Step 3: Replace UI copy and layout**

Rewrite static UI into a compact research console: dashboard, data, factor research, backtest, signals, paper simulation, decision risk, logs. Keep existing endpoints and improve responsive layout.

- [ ] **Step 4: Verify green**

Run GUI tests, `node --check src\quant_robot\gui\static\app.js`, and open the local GUI when practical.

## Task 7: Full Verification

- [ ] Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
```

Expected: all local checks pass, with optional provider readiness still reflecting local environment state.
