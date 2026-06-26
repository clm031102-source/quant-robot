# Round101 Capacity-Safe Price-Volume Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Round101 preregistration gate for capacity-safe public price-volume CN stock factor candidates.

**Architecture:** Add a small op that returns a structured preregistration payload, a CLI that writes JSON/Markdown/CSV artifacts, and startup-gate updates that force Round102 into an Alphalens-style prescreen. Tests lock the no-promotion and no-portfolio-before-prescreen policy.

**Tech Stack:** Python dataclasses, stdlib JSON/CSV, unittest, existing startup-gate config.

---

### Task 1: Preregistration Tests

**Files:**
- Create: `tests/unit/test_capacity_safe_price_volume_preregistration.py`
- Create: `tests/unit/test_capacity_safe_price_volume_preregistration_cli.py`

- [x] Write failing tests that import the new op and CLI.
- [x] Assert at least 8 candidates, public reference tags, capacity filters, and no promotion.
- [x] Assert duplicate names and insufficient count create blockers.
- [x] Run `python -m unittest tests.unit.test_capacity_safe_price_volume_preregistration tests.unit.test_capacity_safe_price_volume_preregistration_cli` and verify the imports fail before implementation.

### Task 2: Preregistration Implementation

**Files:**
- Create: `src/quant_robot/ops/capacity_safe_price_volume_preregistration.py`
- Create: `scripts/run_capacity_safe_price_volume_preregistration.py`

- [x] Add `CapacitySafePriceVolumeCandidateSpec`.
- [x] Add 10 public-reference-inspired candidates.
- [x] Add blockers for duplicates, too few candidates, missing references, missing capacity filters, portfolio preapproval, and promotion preapproval.
- [x] Add JSON/Markdown/CSV writer.
- [x] Add CLI with `--output-dir`, `--min-candidates`, and `--allow-not-ready`.
- [x] Run the new tests and verify they pass.

### Task 3: Round101 Run And Docs

**Files:**
- Create: `docs/research/cn_stock_capacity_safe_price_volume_preregistration_round101_2026-06-22.md`
- Create: `docs/research/cn_stock_work_report_round1_101_2026-06-22.md`

- [x] Run `python scripts\run_capacity_safe_price_volume_preregistration.py --output-dir data\reports\capacity_safe_price_volume_preregistration_round101_20260622 --min-candidates 8`.
- [x] Record candidate count, blocker count, promotion status, and next gate.
- [x] Summarize historical work and bright data without promoting rejected results.

### Task 4: Startup Gate Update

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [x] Set source audit to the Round101 report.
- [x] Set next direction to `round102_capacity_safe_price_volume_alphalens_style_prescreen`.
- [x] Add rejected directions for random formula search and portfolio grid before IC/quantile/turnover prescreen.
- [x] Add required designs for prescreen, candidate correlation deduplication, and turnover decay before walk-forward.
- [x] Add Round101/Round102 confirmations.

### Task 5: Verification

- [x] Run targeted unit tests.
- [x] Run startup gate.
- [x] Run project audit.
- [x] Run `git diff --check`.
- [x] Inspect git status and report final scope.
