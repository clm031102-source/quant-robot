# Round150 Candidate Plan Control Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hard pre-mining control gate for CN stock factor candidate plans.

**Architecture:** Keep preregistration artifacts as the source of candidate intent, then run a separate gate that checks required control declarations and stage permissions. Wire the startup gate so every future factor-mining round sees this requirement before candidate generation.

**Tech Stack:** Python stdlib, JSON/Markdown artifacts, `unittest`, existing `scripts/run_*` pattern.

---

### Task 1: Candidate Plan Gate

**Files:**
- Create: `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- Test: `tests/unit/test_factor_mining_candidate_plan_gate.py`

- [x] Write failing tests for all required control areas, early portfolio/promotion blockers, promotion-quality-gate dependency, and packet validation.
- [x] Implement the gate builder, default control plan, Markdown renderer, JSON writer, and validator.
- [x] Run `python -m unittest tests.unit.test_factor_mining_candidate_plan_gate`.

### Task 2: CLI

**Files:**
- Create: `scripts/run_factor_mining_candidate_plan_gate.py`
- Test: `tests/unit/test_factor_mining_candidate_plan_gate_cli.py`

- [x] Write failing CLI test that validates a candidate-plan JSON and writes JSON/Markdown outputs.
- [x] Implement CLI with `--candidate-plan`, optional `--quality-gate`, `--gate-stage`, and `--allow-blocked`.
- [x] Run `python -m unittest tests.unit.test_factor_mining_candidate_plan_gate_cli`.

### Task 3: Active Round150 Wiring

**Files:**
- Modify: `src/quant_robot/ops/lottery_extreme_upside_reversal_preregistration.py`
- Modify: `tests/unit/test_lottery_extreme_upside_reversal_preregistration.py`

- [x] Require the Round149/Round150 lottery preregistration artifact to carry `research_control_plan`.
- [x] Verify that the generic candidate plan gate clears research screening and keeps portfolio grid disabled.

### Task 4: Startup Protocol

**Files:**
- Modify: `src/quant_robot/ops/factor_mining_startup.py`
- Modify: `tests/unit/test_factor_mining_startup_gate.py`

- [x] Add candidate-plan control items to default required experiment design.
- [x] Add matching per-run confirmations.
- [x] Add validator and pre-run checklist/confirmation text.

### Task 5: Verification

- [x] Regenerate Round149 lottery preregistration artifact.
- [x] Regenerate quality gate packet.
- [x] Run candidate plan gate on the regenerated preregistration artifact.
- [x] Run full targeted unit tests and compile checks.
- [x] Run startup gate confirmation after code changes.
