# Round105 Trend Accumulation Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and run the Round105 long-cycle prescreen for the Round104 capacity-safe trend/amount accumulation CN stock candidates.

**Architecture:** Reuse the Round102 loader, labeler, Alphalens-style summary, and writer helpers. Add a focused Round105 module for trend/amount factor computation plus a CLI wrapper and tests.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops.capacity_safe_price_volume_prescreen` utilities, local processed CN stock bars.

---

## File Map

- Create: `src/quant_robot/ops/capacity_safe_trend_accumulation_prescreen.py`
  - Computes trend/amount accumulation factor values.
  - Calls the shared Round102 prescreen summary.
  - Writes Round105 JSON, Markdown, and CSV outputs.
- Create: `scripts/run_capacity_safe_trend_accumulation_prescreen.py`
  - CLI wrapper around the Round105 module.
- Create: `tests/unit/test_capacity_safe_trend_accumulation_prescreen.py`
  - Unit tests for factor matrix and build flow.
- Create: `tests/unit/test_capacity_safe_trend_accumulation_prescreen_cli.py`
  - Unit test for CLI output writing.
- Modify: `configs/factor_mining_startup_cn_stock.json`
  - Advance source audit and next direction after the real Round105 run.
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
  - Keep startup-gate assertions aligned with the updated config.
- Create: `docs/research/cn_stock_capacity_safe_trend_accumulation_prescreen_round105_2026-06-22.md`
  - Human-readable audit of the real long-cycle run.

## Task 1: Add Failing Unit Tests

- [ ] Create `tests/unit/test_capacity_safe_trend_accumulation_prescreen.py` with tests that import:

```python
from quant_robot.ops.capacity_safe_trend_accumulation_prescreen import (
    build_capacity_safe_trend_accumulation_prescreen,
    compute_capacity_safe_trend_accumulation_factors,
)
```

- [ ] Test that `compute_capacity_safe_trend_accumulation_factors()` returns ten unique factor names, including `volume_weighted_momentum_quality_20`, `amount_accumulation_breakout_20_60`, and `turnover_expansion_momentum_10_40`.
- [ ] Test that no factor name contains `bollinger`, `rsi`, `donchian`, `range_contraction`, or `lowvol_reversal`.
- [ ] Test that all output rows satisfy `amount >= 10000000`.
- [ ] Test that `build_capacity_safe_trend_accumulation_prescreen()` returns stage `capacity_safe_trend_accumulation_prescreen`, candidate count `10`, excludes 2026 final holdout by default, and sets `promotion_allowed` to `False`.
- [ ] Create `tests/unit/test_capacity_safe_trend_accumulation_prescreen_cli.py` and assert that the CLI writes:
  - `capacity_safe_trend_accumulation_prescreen.json`
  - `capacity_safe_trend_accumulation_prescreen.md`
  - `capacity_safe_trend_accumulation_prescreen_results.csv`
  - `capacity_safe_trend_accumulation_prescreen_ic_observations.csv`
- [ ] Run:

```powershell
python -m unittest tests.unit.test_capacity_safe_trend_accumulation_prescreen tests.unit.test_capacity_safe_trend_accumulation_prescreen_cli
```

Expected result before implementation: import failure for the missing module.

## Task 2: Implement Round105 Module

- [ ] Create `src/quant_robot/ops/capacity_safe_trend_accumulation_prescreen.py`.
- [ ] Import Round104 candidate specs and Round102 shared helpers:

```python
from quant_robot.ops.capacity_safe_trend_accumulation_preregistration import (
    default_capacity_safe_trend_accumulation_candidate_specs,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    load_capacity_safe_bars,
    render_capacity_safe_price_volume_prescreen_markdown,
    summarize_capacity_safe_price_volume_prescreen,
)
```

- [ ] Implement `compute_capacity_safe_trend_accumulation_factors()` using per-asset rolling features, date-level z-scores, and the Round104 candidate formulas.
- [ ] Implement `build_capacity_safe_trend_accumulation_prescreen()` to load bars, compute factors, build forward returns, call the shared summary, and rewrite stage/promotion metadata.
- [ ] Implement `write_capacity_safe_trend_accumulation_prescreen()` to write JSON, Markdown, results CSV, and IC observation CSV.
- [ ] Implement `render_capacity_safe_trend_accumulation_prescreen_markdown()` by adapting the shared Round102 markdown text and title.

## Task 3: Implement CLI

- [ ] Create `scripts/run_capacity_safe_trend_accumulation_prescreen.py`.
- [ ] Mirror the Round102 CLI arguments:
  - `--bars-root`
  - `--output-dir`
  - `--analysis-start-date`
  - `--analysis-end-date`
  - `--include-final-holdout`
  - `--horizons`
  - `--execution-lag`
  - `--min-cross-section`
  - `--min-ic-observations`
  - `--min-signal-date-amount`
- [ ] Print a compact JSON payload with summary, data window, and output directory.

## Task 4: Verify Unit Behavior

- [ ] Run the new tests:

```powershell
python -m unittest tests.unit.test_capacity_safe_trend_accumulation_prescreen tests.unit.test_capacity_safe_trend_accumulation_prescreen_cli
```

Expected result after implementation: all new tests pass.

- [ ] Run related regression tests:

```powershell
python -m unittest tests.unit.test_capacity_safe_price_volume_prescreen tests.unit.test_capacity_safe_trend_accumulation_preregistration
```

Expected result: existing prescreen and preregistration tests still pass.

## Task 5: Run Real Long-Cycle Prescreen

- [ ] Run:

```powershell
python scripts\run_capacity_safe_trend_accumulation_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\capacity_safe_trend_accumulation_prescreen_round105_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

- [ ] Capture candidate count, factor rows, label rows, aligned rows, research lead count, FDR-significant count, top rows, and blockers.

## Task 6: Write Audit Report and Update Startup Gate

- [ ] Create `docs/research/cn_stock_capacity_safe_trend_accumulation_prescreen_round105_2026-06-22.md` with:
  - command run
  - data window
  - headline counts
  - top results
  - lead/no-lead conclusion
  - next direction
- [ ] Update `configs/factor_mining_startup_cn_stock.json`:
  - `source_audit` points to the Round105 report.
  - `next_direction` becomes a dedup bridge if leads exist, otherwise a family rotation.
  - add `round105_trend_accumulation_prescreen_read`.
  - add blockers preventing trend/accumulation portfolio grids before dedup.
- [ ] Update startup-gate unit assertions to match the new source audit and next direction.

## Task 7: Final Verification

- [ ] Run:

```powershell
python -m unittest tests.unit.test_capacity_safe_trend_accumulation_prescreen tests.unit.test_capacity_safe_trend_accumulation_prescreen_cli tests.unit.test_capacity_safe_price_volume_prescreen tests.unit.test_capacity_safe_trend_accumulation_preregistration tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] Run:

```powershell
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

- [ ] Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --market CN --asset-type stock --confirm-start --output-dir data\reports\startup_gate_round105_20260622
```

- [ ] Run:

```powershell
python scripts\run_project_audit.py --json
```

- [ ] Run:

```powershell
python -m py_compile src\quant_robot\ops\capacity_safe_trend_accumulation_prescreen.py scripts\run_capacity_safe_trend_accumulation_prescreen.py
```

- [ ] Run:

```powershell
git diff --check
```

Expected result: all required commands either pass or any warnings are explicitly reported.

## Self-Review

- The plan covers all design requirements.
- No placeholders, deferred work, or unspecified "add tests" steps remain.
- Type names and file names are consistent across tasks.
- Commits are intentionally omitted because current task context does not allow commits or pushes.
