# Strict Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn strict audit findings into executable research and verification guardrails.

**Architecture:** Keep changes local and narrow. `run_checks.py` owns check-process hygiene, `walk_forward.py` owns OOS validation status, `alpha_factory.py` owns Alpha Factory paper-candidate gates, and `pipeline.py` owns IC summary significance semantics.

**Tech Stack:** Python 3.12, unittest, pandas, existing Quant Robot modules.

---

### Task 1: Check Runner Source-Tree Hygiene

**Files:**
- Modify: `scripts/run_checks.py`
- Modify: `tests/unit/test_check_plan.py`
- Modify: `README.md`

- [ ] Add tests asserting the child environment prepends `src` and project root to `PYTHONPATH`.
- [ ] Add tests asserting executable check steps run with that environment and project root cwd.
- [ ] Implement helper functions in `run_checks.py` and use them for every subprocess.
- [ ] Update README commands to prefer `.\.venv\Scripts\python.exe`.

### Task 2: Walk-Forward Multiple-Testing Gate

**Files:**
- Modify: `src/quant_robot/validation/walk_forward.py`
- Modify: `tests/unit/test_walk_forward.py`

- [ ] Add a failing test where an accepted row with adjusted IC failure becomes rejected.
- [ ] Apply multiple-testing evidence before final ranking and rewrite rejection reasons consistently.
- [ ] Verify existing walk-forward tests still pass.

### Task 3: Alpha Factory Candidate Gate Hardening

**Files:**
- Modify: `src/quant_robot/research/alpha_factory.py`
- Modify: `scripts/run_tushare_alpha_factory.py`
- Modify: `scripts/run_tushare_alpha_factory_gate.py`
- Modify: `tests/unit/test_alpha_factory.py`
- Modify: `tests/unit/test_tushare_alpha_factory_cli.py`
- Modify: `tests/unit/test_tushare_alpha_factory_gate.py`

- [ ] Add tests for default `min_trades=30`, minimum IC and long-short observation gates, and strict capacity-cost requirements.
- [ ] Add CLI controls for the new observation thresholds and strict capacity-cost mode.
- [ ] Keep existing smoke tests explicit by passing low thresholds where appropriate.
- [ ] Verify Alpha Factory rejects underpowered or uncosted candidates with named reasons.

### Task 4: Tiny-Sample Significance Protection

**Files:**
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `tests/unit/test_research_pipeline.py`

- [ ] Add tests proving one or two IC observations cannot become significant.
- [ ] Add tests proving zero-variance IC samples are marked insufficient.
- [ ] Implement minimal significance guard while preserving existing output keys.

### Task 5: Verification and Git

**Files:**
- Modify: documentation only if command text or policy needs updating.

- [ ] Run targeted unit tests after each task.
- [ ] Run the full local unit suite.
- [ ] Run compile, project audit, and laptop profile checks.
- [ ] Check git status for forbidden data paths.
- [ ] Commit and push `codex/factor-batch-moneyflow-alpha`.
