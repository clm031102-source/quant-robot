# Round159 Eight-Gap Optimization And Tradeability Event Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the eight user-identified factor-mining weaknesses into startup-gate confirmations, then rotate Round159 into A-share real tradeability/limit-event hypotheses.

**Architecture:** Extend the CN stock startup protocol with explicit per-run controls for A-share tradeability, PIT financial timing, neutralization, ETF boundary, portfolio construction, strict statistics, China regimes, and events. Add a small preregistration module and CLI for Round159 tradeability/limit-event candidates; this produces no promotion claims and only unlocks a later proxy prescreen.

**Tech Stack:** Python, JSON startup config, `unittest`, existing preregistration writer patterns.

---

### Task 1: Startup-Gate Optimization Coverage

**Files:**
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
- Modify: `configs/factor_mining_startup_cn_stock.json`

- [ ] **Step 1: Write failing test**

Require the default CN stock startup packet to include explicit required experiment design and per-run confirmation items for all eight optimization categories from the user screenshot.

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_requires_round159_eight_gap_optimization_controls`

Expected: FAIL until the config contains the new controls.

- [ ] **Step 3: Add config controls**

Update `required_confirmations` and `research_direction.repeatable_mining_protocol` so every future factor-mining start must confirm the eight controls.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_requires_round159_eight_gap_optimization_controls`

Expected: PASS.

### Task 2: Round159 Tradeability Event Preregistration

**Files:**
- Create: `tests/unit/test_cn_tradeability_limit_event_preregistration.py`
- Create: `tests/unit/test_cn_tradeability_limit_event_preregistration_cli.py`
- Create: `src/quant_robot/ops/cn_tradeability_limit_event_preregistration.py`
- Create: `scripts/run_cn_tradeability_limit_event_preregistration.py`
- Create: `docs/research/cn_stock_cn_tradeability_limit_event_preregistration_round159_2026-06-23.md`

- [ ] **Step 1: Write failing tests**

Require eight non-moneyflow, non-RSRS, non-price-volume-shock candidates with true-limit-status audit requirements, ST/suspension/new-listing controls, and no portfolio or promotion permission.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.unit.test_cn_tradeability_limit_event_preregistration tests.unit.test_cn_tradeability_limit_event_preregistration_cli`

Expected: FAIL because the module and CLI do not exist.

- [ ] **Step 3: Implement minimal preregistration**

Create candidate specs, summary, blockers, markdown/JSON/CSV writers, and CLI output.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.unit.test_cn_tradeability_limit_event_preregistration tests.unit.test_cn_tradeability_limit_event_preregistration_cli`

Expected: PASS.

### Task 3: Round159 Output, Three-Round Review, And Verification

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
- Create: `docs/research/cn_stock_round157_159_three_round_review_2026-06-23.md`

- [ ] **Step 1: Run real preregistration**

Run: `python scripts\run_cn_tradeability_limit_event_preregistration.py --output-dir data\reports\cn_tradeability_limit_event_preregistration_round159_20260623`

- [ ] **Step 2: Update startup direction**

Set source audit to the Round157-159 review and next direction to `round160_cn_tradeability_limit_event_proxy_prescreen`; keep failed price-volume-shock directions rejected.

- [ ] **Step 3: Verify**

Run focused unit tests, py_compile for new files, JSON validation for the startup config, the startup gate, and `git ls-files data/raw data/processed data/reports`.
