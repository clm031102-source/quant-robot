# Round107 Negative-IC Trend Accumulation Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the Round107 long-cycle prescreen for the 10 pre-registered negative-IC trend/amount accumulation candidates.

**Architecture:** Add a focused operation module that reuses the existing Round105 feature matrix and Round102 prescreen summary engine. Add a CLI wrapper, unit tests, and a lightweight research report after the real run.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops` prescreen helpers, local DatasetStore test fixtures.

---

### Task 1: Tests First

**Files:**
- Create: `tests/unit/test_negative_ic_trend_accumulation_prescreen.py`
- Create: `tests/unit/test_negative_ic_trend_accumulation_prescreen_cli.py`

- [ ] **Step 1: Write factor-generation and build tests**

Create tests that import `compute_negative_ic_trend_accumulation_factors` and `build_negative_ic_trend_accumulation_prescreen`, generate synthetic CN bars, assert all 10 Round106 names appear, assert capacity filters hold, assert 2026 holdout data is excluded by default, and assert promotion remains blocked.

- [ ] **Step 2: Write CLI output tests**

Create a CLI test that imports `run_negative_ic_trend_accumulation_prescreen_cli`, writes synthetic bars through `DatasetStore`, runs the CLI, and asserts JSON, Markdown, result CSV, and IC CSV outputs exist.

- [ ] **Step 3: Verify RED**

Run:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_prescreen tests.unit.test_negative_ic_trend_accumulation_prescreen_cli
```

Expected: import failure because the operation module and CLI do not exist yet.

### Task 2: Operation Module

**Files:**
- Create: `src/quant_robot/ops/negative_ic_trend_accumulation_prescreen.py`

- [ ] **Step 1: Add builder and factor computation**

Implement `build_negative_ic_trend_accumulation_prescreen` and `compute_negative_ic_trend_accumulation_factors`. Reuse Round105 `_feature_frame`, `_add_cross_sectional_features`, `_data_window`, `_sanitize`, `_write_csv`, and the Round102 prescreen summarizer.

- [ ] **Step 2: Add report writers**

Write `write_negative_ic_trend_accumulation_prescreen` and `render_negative_ic_trend_accumulation_prescreen_markdown`. Output names must use the `negative_ic_trend_accumulation_prescreen` prefix.

- [ ] **Step 3: Verify GREEN for operation tests**

Run the two new unit test modules and fix only implementation defects.

### Task 3: CLI

**Files:**
- Create: `scripts/run_negative_ic_trend_accumulation_prescreen.py`

- [ ] **Step 1: Add CLI wrapper**

Mirror the Round105 CLI arguments: bars roots, output dir, analysis dates, holdout flag, horizons, execution lag, min cross-section, min IC observations, and min signal-date amount.

- [ ] **Step 2: Verify GREEN for CLI tests**

Run the two new unit test modules and confirm the CLI writes all expected artifacts.

### Task 4: Real Long-Cycle Run

**Files:**
- Generated but not committed: `data/reports/negative_ic_trend_accumulation_prescreen_round107_20260622/*`

- [ ] **Step 1: Run long-cycle prescreen**

Run:

```powershell
python scripts\run_negative_ic_trend_accumulation_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\negative_ic_trend_accumulation_prescreen_round107_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

- [ ] **Step 2: Inspect results**

Read the JSON and CSV output. If `research_lead_count > 0`, set the next direction to `round108_negative_ic_trend_accumulation_lead_dedup`. If zero, set it to `round108_family_rotation_after_negative_ic_prescreen_failure`.

### Task 5: Report and Startup Gate

**Files:**
- Create: `docs/research/cn_stock_negative_ic_trend_accumulation_prescreen_round107_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Write report**

Summarize candidate count, data window, factor rows, label rows, aligned rows, FDR leads, research leads, top rows, blockers, and next direction.

- [ ] **Step 2: Update startup gate**

Point `source_audit` to the Round107 report, set the next direction from the real result, record the Round107 read confirmation, and block same-family tuning or portfolio grids without a prescreen lead.

- [ ] **Step 3: Verify startup gate**

Run the startup gate unit test and the real startup gate command for `office_desktop`, `factor_validation`, CN stock.

### Task 6: Final Verification

**Files:**
- All created or modified source, script, test, config, and docs files.

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_prescreen tests.unit.test_negative_ic_trend_accumulation_prescreen_cli tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] **Step 2: Run syntax/config checks**

Run `python -m json.tool configs\factor_mining_startup_cn_stock.json > $null`, `python -m py_compile` for new Python files, `python scripts\run_project_audit.py --json`, and `git diff --check`.

- [ ] **Step 3: Confirm generated data reports stay ignored**

Run `git status --short --ignored data\reports\negative_ic_trend_accumulation_prescreen_round107_20260622`.
