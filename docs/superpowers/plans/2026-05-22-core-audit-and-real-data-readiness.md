# Core Audit And Real Data Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze GUI work and strengthen the project core with repeatable audit commands, clearer mock/real boundaries, and a safe Tushare real-data smoke-test path.

**Architecture:** Add small Python modules and CLI scripts that inspect the repository, run deterministic checks, and prepare real Tushare ingestion without downloading unless explicitly requested by command flags. Keep all new behavior local, offline by default, and covered by unit tests.

**Tech Stack:** Python standard library, existing `unittest` test suite, existing Tushare ingest pipeline, JSON/Markdown reports.

---

### Task 1: Project Audit Module

**Files:**
- Create: `src/quant_robot/audit/__init__.py`
- Create: `src/quant_robot/audit/project_audit.py`
- Create: `scripts/run_project_audit.py`
- Test: `tests/unit/test_project_audit.py`

- [ ] Write failing tests for forbidden live-trading implementation detection, mock-data boundary detection, and report shape.
- [ ] Implement an audit function that scans only repository-relative paths.
- [ ] Mark documentation boundary text as allowed while flagging implementation-level broker/order code.
- [ ] Implement JSON and Markdown report output.

### Task 2: Standard Check Runner

**Files:**
- Create: `scripts/run_checks.py`
- Test: `tests/unit/test_check_plan.py`

- [ ] Write failing tests for the check command plan.
- [ ] Implement a command planner that includes tests, compile, audit, readiness, and fixture research.
- [ ] Keep command execution explicit and local; no network commands.

### Task 3: Tushare Smoke Plan

**Files:**
- Create: `src/quant_robot/data/tushare_smoke.py`
- Create: `scripts/run_tushare_smoke.py`
- Test: `tests/unit/test_tushare_smoke.py`
- Modify: `docs/phase_1_5_real_data.md`

- [ ] Write failing tests for dry-run readiness and explicit execute mode.
- [ ] Implement dry-run mode that never downloads data.
- [ ] Implement execute mode that calls the existing Tushare ingest pipeline only when dependencies and token are ready.
- [ ] Document the safe dry-run and real smoke commands.

### Task 4: Verification And Publish

**Files:**
- Modify only if verification exposes defects.

- [ ] Run focused tests for the new modules.
- [ ] Run full unit/integration test suite.
- [ ] Run compile check.
- [ ] Run the new audit and smoke dry-run commands.
- [ ] Commit and push the result.
