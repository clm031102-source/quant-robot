# Round152 PIT Profitability Event Revision Matrix Label Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Round152 smoke gate that computes active PIT profitability revision factor values and verifies forward-label alignment before any IC or portfolio work.

**Architecture:** Add one focused ops module and one CLI script. Reuse existing PIT financial loading and forward-label helpers, but implement separate formula mapping for the Round151 active candidates so rejected static profitability factors cannot re-enter by accident.

**Tech Stack:** Python, pandas, unittest, existing `DatasetStore`, existing `make_forward_returns`.

---

### Task 1: Round152 Ops Module

**Files:**
- Create: `src/quant_robot/ops/profitability_event_revision_matrix_label_smoke.py`
- Test: `tests/unit/test_profitability_event_revision_matrix_label_smoke.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

- build Round151 preregistration from synthetic PIT financial rows;
- compute seven active candidates and keep three endpoint candidates frozen;
- attach signal dates strictly after `ann_date`;
- align labels with `entry_date > signal_date`;
- block unknown active formulas;
- block sparse bars when label coverage is too low.

- [ ] **Step 2: Run tests and verify RED**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_matrix_label_smoke`

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement minimal module**

Implement:

- `build_profitability_event_revision_matrix_label_smoke`
- `compute_profitability_event_revision_factor_frame`
- `write_profitability_event_revision_matrix_label_smoke`
- formula helpers for the seven active candidates
- strict alignment and label-coverage summaries

- [ ] **Step 4: Run tests and verify GREEN**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_matrix_label_smoke`

Expected: all tests pass.

### Task 2: Round152 CLI

**Files:**
- Create: `scripts/run_profitability_event_revision_matrix_label_smoke.py`
- Test: `tests/unit/test_profitability_event_revision_matrix_label_smoke_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a CLI runner test that writes JSON, Markdown, and CSV outputs from synthetic data.

- [ ] **Step 2: Run CLI test and verify RED**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_matrix_label_smoke_cli`

Expected: import failure because the script does not exist.

- [ ] **Step 3: Implement CLI**

Implement a narrow wrapper around the ops module with:

- `--financial-root`
- repeated `--bars-root`
- `--preregistration-json`
- optional `--candidate-plan-gate-json`
- repeated `--horizon`
- `--execution-lag`
- `--min-label-coverage`
- `--allow-not-ready`

- [ ] **Step 4: Run CLI test and py_compile**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_matrix_label_smoke_cli`

`python -m py_compile src\quant_robot\ops\profitability_event_revision_matrix_label_smoke.py scripts\run_profitability_event_revision_matrix_label_smoke.py`

Expected: all pass.

### Task 3: Real Round152 Smoke And Report

**Files:**
- Create: `docs/research/cn_stock_profitability_event_revision_matrix_label_smoke_round152_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`

- [ ] **Step 1: Run real Round152 smoke**

Run:

`python scripts\run_profitability_event_revision_matrix_label_smoke.py --financial-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --bars-root data\processed\office_desktop_20260616_combined_research --preregistration-json data\reports\profitability_event_revision_preregistration_round151_20260623\profitability_event_revision_preregistration.json --candidate-plan-gate-json data\reports\factor_mining_candidate_plan_gate_round151_20260623\factor_mining_candidate_plan_gate.json --output-dir data\reports\profitability_event_revision_matrix_label_smoke_round152_20260623 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.6`

- [ ] **Step 2: Write report**

Record active candidates, frozen candidates, label coverage, alignment violations, and next allowed action.

- [ ] **Step 3: Update startup config**

If Round152 passes, move next direction to controlled IC/neutral prescreen. If it fails, move next direction to data/schema repair.

- [ ] **Step 4: Verify**

Run the focused unit tests, startup gate, py_compile, and data-path Git checks before claiming completion.
