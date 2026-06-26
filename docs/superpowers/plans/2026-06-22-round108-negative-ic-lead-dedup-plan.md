# Round108 Negative-IC Lead Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the Round107 `overheat_avoidance_relative_strength_60` research lead for correlation redundancy, capacity cleanliness, and extreme signal-date moves before any portfolio conversion.

**Architecture:** Create a focused operation module that loads CN bars, computes sampled factor matrices for the Round107 lead and selected reference families, computes cross-sectional Spearman correlations, audits lead top-quintile capacity/extreme-return properties, and writes JSON/Markdown/CSV reports. Add a CLI wrapper and unittest coverage using synthetic DatasetStore bars.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops` factor generators, local DatasetStore fixtures.

---

### Task 1: Tests First

**Files:**
- Create: `tests/unit/test_negative_ic_trend_accumulation_lead_dedup.py`
- Create: `tests/unit/test_negative_ic_trend_accumulation_lead_dedup_cli.py`

- [ ] **Step 1: Write failing summarize tests**

Test `summarize_negative_ic_trend_accumulation_lead_dedup` with a synthetic factor frame containing a lead, a hard-blocking duplicate, a source-lineage duplicate, and a unique factor. Assert hard-blocking redundancy creates a blocker, source-lineage redundancy is classified but not hard-blocking, and promotion is false.

- [ ] **Step 2: Write failing build tests**

Test `build_negative_ic_trend_accumulation_lead_dedup` with synthetic CN bars and a prescreen report confirming `overheat_avoidance_relative_strength_60` as a research lead. Assert 2026 holdout exclusion, capacity audit fields, non-promotion, and next direction shape.

- [ ] **Step 3: Write failing CLI tests**

Test `run_negative_ic_trend_accumulation_lead_dedup_cli` writes JSON, Markdown, correlation CSV, correlation-observation CSV, and capacity-observation CSV.

- [ ] **Step 4: Verify RED**

Run:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_lead_dedup tests.unit.test_negative_ic_trend_accumulation_lead_dedup_cli
```

Expected: import failure because the module and CLI do not exist yet.

### Task 2: Operation Module

**Files:**
- Create: `src/quant_robot/ops/negative_ic_trend_accumulation_lead_dedup.py`

- [ ] **Step 1: Implement factor-frame assembly**

Load bars with `load_capacity_safe_bars`, compute sampled factor frames from:

- `compute_negative_ic_trend_accumulation_factors`
- `compute_capacity_safe_trend_accumulation_factors`
- `compute_capacity_safe_price_volume_factors`

Add `reference_family` to each frame.

- [ ] **Step 2: Implement correlation summary**

For each reference factor, merge on `date`, `asset_id`, and `market`, compute per-date Spearman correlation against the lead, summarize mean/max absolute correlation, classify redundancy, and mark hard blockers only for hard-blocking reference families.

- [ ] **Step 3: Implement capacity audit**

For sampled lead dates, rank the lead into quintiles, audit top-quintile amount, ADV20, and signal-date return extremes.

- [ ] **Step 4: Implement report writer**

Write JSON, Markdown, `negative_ic_trend_accumulation_lead_correlations.csv`, `negative_ic_trend_accumulation_lead_correlation_observations.csv`, and `negative_ic_trend_accumulation_lead_capacity_observations.csv`.

### Task 3: CLI

**Files:**
- Create: `scripts/run_negative_ic_trend_accumulation_lead_dedup.py`

- [ ] **Step 1: Add CLI wrapper**

Expose bars roots, prescreen report path, output dir, analysis dates, final holdout flag, sample cadence, min cross-section, min signal-date amount, lead factor, and lead horizon.

- [ ] **Step 2: Verify GREEN**

Run the two new unit test modules and fix implementation defects.

### Task 4: Real Run

**Files:**
- Generated but ignored: `data/reports/negative_ic_trend_accumulation_lead_dedup_round108_20260622/*`

- [ ] **Step 1: Run Round108 audit**

```powershell
python scripts\run_negative_ic_trend_accumulation_lead_dedup.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --prescreen-report data\reports\negative_ic_trend_accumulation_prescreen_round107_20260622\negative_ic_trend_accumulation_prescreen.json --output-dir data\reports\negative_ic_trend_accumulation_lead_dedup_round108_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --sample-every-n-dates 5 --min-cross-section 30 --min-signal-date-amount 10000000
```

- [ ] **Step 2: Inspect result**

If no gate blockers appear, next direction is `round109_overheat_relative_strength_cost_capacity_bridge`. If blockers appear, next direction is `round109_family_rotation_after_round108_dedup_failure`.

### Task 5: Report And Startup Gate

**Files:**
- Create: `docs/research/cn_stock_negative_ic_trend_accumulation_lead_dedup_round108_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Write Round108 report**

Summarize lead evidence, redundancy classes, hard blockers, capacity audit, next direction, and rejected next work.

- [ ] **Step 2: Update startup gate**

Point `source_audit` to Round108, set next direction from the real audit, add Round108 read confirmation, and reject portfolio grid or parameter tuning before the decided next gate.

### Task 6: Verification

**Files:**
- All new and modified files.

- [ ] **Step 1: Run focused tests**

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_lead_dedup tests.unit.test_negative_ic_trend_accumulation_lead_dedup_cli tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] **Step 2: Run safety checks**

Run JSON validation, `py_compile` for new files, startup gate, project audit, `git diff --check`, and ignored data-report status.
