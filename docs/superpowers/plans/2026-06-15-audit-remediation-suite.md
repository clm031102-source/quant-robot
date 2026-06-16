# Audit Remediation Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the strict audit into enforceable validation, cost, quality, promotion, and execution-boundary controls.

**Architecture:** Extend existing modules in place, preserving backward compatibility for current configs and artifacts. Add strict evidence fields and gates that fail closed when data is missing.

**Tech Stack:** Python 3.11, pandas, unittest, existing local artifact writers.

---

### Task 1: Rolling Walk-Forward Validation

**Files:**
- Modify: `src/quant_robot/validation/walk_forward.py`
- Modify: `tests/unit/test_walk_forward.py`
- Modify: `tests/unit/test_walk_forward_cli.py`

- [x] Write failing tests for rolling fold generation and aggregated case metrics.
- [x] Run the focused walk-forward tests and confirm failure.
- [x] Add optional rolling config fields while keeping existing `split_date` behavior.
- [x] Aggregate train/test results across folds with fold counts and worst-fold metrics.
- [x] Run focused tests.

### Task 2: Statistical Evidence

**Files:**
- Modify: `src/quant_robot/research/ic.py`
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/validation/walk_forward.py`
- Modify: `tests/unit/test_research.py`
- Modify: `tests/unit/test_research_pipeline.py`
- Modify: `tests/unit/test_experiment_runner.py`

- [x] Write failing tests for IC t-statistics, approximate p-values, positive IC rate, and significance status.
- [x] Run focused tests and confirm failure.
- [x] Implement statistical fields with stdlib math only.
- [x] Propagate fields into experiment and validation leaderboards.
- [x] Run focused tests.

### Task 3: Cost And Capacity Model

**Files:**
- Modify: `src/quant_robot/backtest/costs.py`
- Modify: `src/quant_robot/backtest/engine.py`
- Modify: `src/quant_robot/paper/simulator.py`
- Modify: `tests/unit/test_backtest.py`
- Modify: `tests/unit/test_paper_simulation.py`

- [x] Write failing tests for market impact and participation evidence.
- [x] Run focused tests and confirm failure.
- [x] Implement structured cost decomposition and retain `cost_bps` compatibility.
- [x] Include cost fields in backtest trades, paper fills, and metrics when data is available.
- [x] Run focused tests.

### Task 4: Data Quality Evidence

**Files:**
- Modify: `src/quant_robot/data/quality_report.py`
- Modify: `src/quant_robot/data/quality.py`
- Modify: `tests/unit/test_quality_report.py`

- [x] Write failing tests for extreme returns, stale prices, and adjusted-close jumps.
- [x] Run focused tests and confirm failure.
- [x] Implement additional report fields without breaking existing quality report consumers.
- [x] Run focused tests.

### Task 5: Promotion And Readiness Gates

**Files:**
- Modify: `src/quant_robot/promotion/gate.py`
- Modify: `src/quant_robot/ops/paper_ops_guardrail.py`
- Modify: `tests/unit/test_promotion_gate.py`
- Modify: `tests/unit/test_paper_ops_guardrail.py`

- [x] Write failing tests proving weak statistical evidence, short rolling evidence, stale providers, and severe data-quality issues cannot pass strict promotion gates.
- [x] Run focused tests and confirm failure.
- [x] Add strict evidence gating with backward-compatible defaults.
- [x] Run focused tests.

### Task 6: Execution Boundary Scaffolding

**Files:**
- Create: `src/quant_robot/execution/__init__.py`
- Create: `src/quant_robot/execution/boundary.py`
- Create: `tests/unit/test_execution_boundary.py`

- [x] Write failing tests for read-only snapshot, manual approval packet, kill switch, and order-placement refusal.
- [x] Run focused tests and confirm failure.
- [x] Implement the execution boundary module.
- [x] Run focused tests.

### Task 7: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/progress_audit_2026-06-15.md`

- [x] Update status text to distinguish code remediation from non-code live-profit evidence.
- [x] Run `python -m unittest discover -s tests -p "test_*.py"`.
- [x] Run `python -m compileall -q src scripts tests`.
- [x] Run `python scripts/run_project_audit.py --json`.
- [x] Record remaining external evidence gates in the final report.
