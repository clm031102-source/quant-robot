# Round116 Public Alpha101 Reference Exposure Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the Round115 public Alpha101/Qlib research lead for redundancy, hidden exposure, and period instability.

**Architecture:** Add a public Alpha101 dedup module that computes the lead, reference factors, and exposure diagnostics from the same bars, then reuses Round112-style correlation and IC stability helpers. Add a CLI wrapper and report.

**Tech Stack:** Python, pandas, existing public Alpha101 prescreen, capacity-safe price-volume factors, market-residual exposure factors, existing Round112 audit helpers, `unittest`.

---

### Task 1: Summary Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_reference_exposure_dedup.py`

- [ ] **Step 1: Write failing test**

Use synthetic factor/label/reference/exposure frames to prove high redundancy, high exposure, and 2015 failure become blockers while promotion remains false.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_reference_exposure_dedup`

Expected: fail because the module does not exist.

### Task 2: CLI Tests

**Files:**
- Create: `tests/unit/test_public_alpha101_reference_exposure_dedup_cli.py`

- [ ] **Step 1: Write failing CLI test**

Use synthetic bars and a synthetic Round115 prescreen JSON to prove the CLI writes JSON/Markdown/reference/exposure/yearly/monthly CSV outputs.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.unit.test_public_alpha101_reference_exposure_dedup_cli`

Expected: fail because the script does not exist.

### Task 3: Implementation

**Files:**
- Create: `src/quant_robot/ops/public_alpha101_reference_exposure_dedup.py`
- Create: `scripts/run_public_alpha101_reference_exposure_dedup.py`

- [ ] **Step 1: Build lead/reference/exposure frames**

Compute the public Alpha101 lead, capacity-safe reference factors, and market-residual exposure frame with the same date/asset universe.

- [ ] **Step 2: Summarize audit**

Calculate lead IC, yearly/monthly failures, reference correlations, exposure correlations, blockers, and next direction.

- [ ] **Step 3: Write artifacts**

Write JSON, Markdown, reference correlations CSV, exposure correlations CSV, yearly/monthly IC CSV, and IC observations CSV.

### Task 4: Runtime And Verification

**Files:**
- Create: `docs/research/cn_stock_public_alpha101_reference_exposure_dedup_round116_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Run real Round116**

Run against local 2015-2025 bars using sampled correlation dates.

- [ ] **Step 2: Advance startup gate**

Set source audit to Round116 report and next direction to `round117_round114_116_three_round_review_before_next_action`.

- [ ] **Step 3: Verify**

Run unit tests, startup gate, project audit, `py_compile`, and `git diff --check`.

Commit step is deferred because current startup context says commits and pushes are not allowed.
