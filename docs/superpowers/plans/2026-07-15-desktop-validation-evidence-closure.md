# Desktop Validation Evidence Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans or superpowers:subagent-driven-development task by task.

**Goal:** Make the frozen CN stock residual-regime desktop validation reproducible from authority data and a provider-backed calendar while preserving fail-closed promotion and final-holdout boundaries.

**Architecture:** Add a small calendar evidence module and a validation-specific readiness contract, extend existing authority loaders into the walk-forward/data-manifest entrypoints, and give the stock gap audit an explicit review state for unclassified suspension gaps. Rewire the desktop profile around those contracts.

**Tech Stack:** Python 3.11+, pandas, pathlib, hashlib, JSON/CSV, unittest/pytest, Tushare adapter.

---

### Task 1: Provider Calendar Artifact And Provenance

**Files:**
- Create: `src/quant_robot/data/cn_trading_calendar.py`
- Create: `scripts/run_cn_trading_calendar.py`
- Create: `tests/unit/test_cn_trading_calendar.py`
- Create: `tests/unit/test_cn_trading_calendar_cli.py`

- [x] Write failing tests for synchronized SSE/SZSE construction, exchange divergence, empty source data, duplicate dates, atomic artifact output, and SHA-256 tamper detection.
- [x] Run the focused tests and verify RED.
- [x] Implement calendar construction, manifest writing, manifest validation, Tushare fetch, and validate-only CLI mode.
- [x] Run the focused tests and verify GREEN.
- [x] Commit as `feat: add provider-backed CN trading calendar`.

### Task 2: Stock-Aware Gap Audit State

**Files:**
- Modify: `src/quant_robot/data/gap_audit.py`
- Modify: `scripts/run_data_quality_audit.py`
- Modify: `tests/unit/test_data_quality_gap_audit.py`
- Modify: `tests/unit/test_data_quality_gap_audit_cli.py`

- [x] Add failing tests for `asset_gap_policy=review`, whole-market hard blockers, review-required CLI exit behavior, and calendar-manifest provenance.
- [x] Run focused tests and verify RED.
- [x] Implement `block` and `review` policies, preserve strict default behavior, and add `--allow-review-required` plus calendar-manifest validation.
- [x] Run focused tests and verify GREEN.
- [x] Commit as `fix: classify stock calendar gaps honestly`.

### Task 3: Authority Data Manifest

**Files:**
- Modify: `src/quant_robot/storage/fingerprints.py`
- Modify: `src/quant_robot/ops/cn_stock_data_manifest.py`
- Modify: `scripts/run_cn_stock_data_manifest.py`
- Modify: `tests/unit/test_cn_stock_data_manifest.py`
- Modify: `tests/unit/test_cn_stock_data_manifest_cli.py`

- [x] Add failing tests for authority bar configs, separate moneyflow authority configs, referenced dataset fingerprints, and tampered segment files.
- [x] Run focused tests and verify RED.
- [x] Implement authority-dataset inventory fingerprints and record/validate both source roots.
- [x] Run focused tests and verify GREEN.
- [x] Commit as `fix: bind CN manifests to authority datasets`.

### Task 4: Validation-Specific Readiness Contract

**Files:**
- Create: `src/quant_robot/ops/factor_validation_readiness.py`
- Create: `scripts/run_factor_validation_readiness.py`
- Create: `tests/unit/test_factor_validation_readiness.py`
- Create: `tests/unit/test_factor_validation_readiness_cli.py`

- [x] Add failing tests for config/factor/source mismatches, stale startup or data manifests, calendar gaps, post-2025 data, changed fingerprints, final-holdout access, and live permission.
- [x] Run focused tests and verify RED.
- [x] Implement packet build/write/validate functions and CLI generation.
- [x] Run focused tests and verify GREEN.
- [x] Commit as `feat: bind frozen factor validation evidence`.

### Task 5: Authority Walk-Forward Source

**Files:**
- Modify: `scripts/run_walk_forward.py`
- Modify: `scripts/run_desktop_factor_validation.py`
- Modify: `configs/walk_forward_tushare_moneyflow_residual_regime.json`
- Modify: `tests/unit/test_walk_forward_cli.py`
- Modify: `tests/unit/test_desktop_factor_validation.py`

- [x] Add failing tests for `authority-bars`, file-only authority roots, exact validation packet matching, and rejection of implicit gate bypasses.
- [x] Run focused tests and verify RED.
- [x] Add the authority loader, dual readiness-gate enforcement, repaired moneyflow config, and authority defaults.
- [x] Run focused tests and verify GREEN.
- [x] Commit as `fix: run desktop validation from authority inputs`.

### Task 6: Desktop Profile Rewire

**Files:**
- Modify: `scripts/run_checks.py`
- Modify: `scripts/run_desktop_validation_summary.py`
- Modify: `README.md`
- Modify: `docs/research/desktop_residual_regime_validation_runbook_2026-06-16.md`
- Modify: `tests/unit/test_run_checks.py`
- Modify: `tests/unit/test_desktop_validation_summary.py`

- [ ] Add failing tests for exact profile order, authority paths, calendar validation, review-required quality audit, validation readiness, and summary quality status.
- [ ] Run focused tests and verify RED.
- [ ] Rewire the profile, remove its unscoped catalog scan, and update operator documentation.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit as `fix: close desktop validation evidence chain`.

### Task 7: Real Evidence Run And Failure Repair

- [ ] Fetch and write the real Tushare SSE/SZSE calendar for 2015-2025.
- [ ] Validate the calendar artifact and manifest.
- [ ] Generate the authority CN data manifest.
- [ ] Run the stock-aware quality audit and record its exact review/blocker counts.
- [ ] Generate the factor-validation readiness packet.
- [ ] Run `desktop-validation` and repair code defects using systematic debugging; after three repetitions of the same external blocker, stop that path and document the blocker instead of looping.
- [ ] Confirm the promotion report remains research-only or blocked unless every evidence contract genuinely clears.

### Task 8: Final Verification, Audit Report, And Commit

- [ ] Run all focused tests changed in Tasks 1-6.
- [ ] Run the complete unit/integration suite.
- [ ] Run compile checks, project audit, maintainability audit, and `git diff --check`.
- [ ] Write `docs/research/desktop_validation_evidence_closure_2026-07-15.md` with completion, feasibility, defects fixed, unresolved evidence gaps, and current profitability judgment.
- [ ] Update the implementation checklist and commit final documentation as `docs: report desktop validation evidence closure`.
- [ ] Do not push from the office desktop.
