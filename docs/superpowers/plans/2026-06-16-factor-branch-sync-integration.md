# Factor Branch Sync Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate useful office-desktop moneyflow factor work into core code and make future `同步项目` runs detect unintegrated remote research branches.

**Architecture:** Core research code is merged from the office factor branch while preserving the current sync script. A manifest records absorbed branch commits, and sync audits compare remote branch heads with that manifest.

**Tech Stack:** Python 3.11+, stdlib `unittest`, Git CLI, pandas/numpy research modules.

---

### Task 1: Protect Sync Audit Behavior

**Files:**
- Modify: `tests/unit/test_sync_project.py`
- Modify: `scripts/sync_project.py`
- Create: `configs/factor_branch_integration_manifest.json`

- [ ] **Step 1: Write failing tests**

Add tests that call manifest/audit helpers directly:

```python
def test_reports_unabsorbed_remote_research_branch(self) -> None:
    pending = audit_remote_research_branches(
        [
            {"name": "origin/codex/factor-batch-moneyflow-alpha", "commit": "abc123"},
            {"name": "origin/main", "commit": "def456"},
        ],
        {"absorbed_branches": []},
        current_commits=set(),
    )
    self.assertEqual(pending[0]["branch"], "origin/codex/factor-batch-moneyflow-alpha")


def test_execute_blocks_core_sync_when_research_branch_is_pending(self) -> None:
    plan = build_sync_plan(
        _config(),
        current_branch="codex/project-audit-2026-06-16",
        changed_paths=["src/quant_robot/factors/example.py"],
        machine="laptop",
        task="architecture_ops",
        execute=True,
        push=True,
        upstream_sync="0\t0",
        pending_research_branches=[{"branch": "origin/codex/factor-batch-moneyflow-alpha"}],
    )
    self.assertIn("pending_research_branches_require_integration", plan["blockers"])
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `python -m unittest tests.unit.test_sync_project -v`

Expected: imports or assertions fail because the audit helper and blocker do not exist yet.

- [ ] **Step 3: Implement minimal sync audit helpers**

Add remote branch pattern matching, manifest loading, pending-branch audit output, and execute blockers for core sync tasks.

- [ ] **Step 4: Run targeted tests**

Run: `python -m unittest tests.unit.test_sync_project -v`

Expected: all sync-project tests pass.

### Task 2: Merge Useful Factor Branch Content

**Files:**
- Merge from: `origin/codex/factor-batch-moneyflow-alpha`
- Preserve: `scripts/sync_project.py`
- Resolve: README/workstation/config drift in favor of current sync protocol plus useful research additions.

- [ ] **Step 1: Merge without committing**

Run: `git merge --no-commit --no-ff origin/codex/factor-batch-moneyflow-alpha`

- [ ] **Step 2: Resolve conflicts conservatively**

Keep current `scripts/sync_project.py`; retain the current startup protocol; accept useful research modules, configs, tests, and docs.

- [ ] **Step 3: Update integration manifest**

Record `origin/codex/factor-batch-moneyflow-alpha` at `008bdf3c817617230d56f4ea4295e26d459860c7` as absorbed into core.

### Task 3: Verify Core Integration

**Files:**
- Existing project files touched by merge and sync audit.

- [ ] **Step 1: Run targeted tests**

Run: `python -m unittest tests.unit.test_sync_project tests.unit.test_moneyflow_technical_combo_factors tests.unit.test_research_pipeline tests.unit.test_alpha_factory -v`

- [ ] **Step 2: Run project checks**

Run: `python scripts/run_checks.py --profile laptop --execute`

- [ ] **Step 3: Run sync audit**

Run: `python scripts/sync_project.py --machine laptop --task architecture_ops`

Expected: no forbidden paths and no pending branch blocker for the absorbed moneyflow branch.

### Task 4: Commit And Push

**Files:**
- All verified syncable files only.

- [ ] **Step 1: Review changed paths**

Run: `git status --short`

- [ ] **Step 2: Commit through sync script when safe**

Run: `python scripts/sync_project.py --machine laptop --task architecture_ops --execute --push --message "Integrate moneyflow factor branch sync safeguards"`

- [ ] **Step 3: Confirm push state**

Run: `git status --short --branch`

Expected: branch clean and aligned with upstream.
