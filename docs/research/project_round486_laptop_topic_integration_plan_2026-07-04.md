# Project Round486 Laptop Topic Integration Plan

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: reduce the remaining mainline integration risk by adding a laptop-owned topic-branch integration plan generator.

## Progress Snapshot

Estimated project completion remains 98%.

The project still has three durable blockers before profit-factor mining:

```text
not_on_stable_branch
remote_topic_branches_remaining
observation_sufficiency_not_cleared
```

This round does not mutate `main` or delete remote branches from the office desktop. It makes the laptop-owned integration path explicit and machine-checkable.

## Change

New script:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

The script prints a JSON plan. It discovers `origin/codex/*` topic branches, skips branches already present in stable `main` or absorbed/ignored by `configs/factor_branch_integration_manifest.json`, orders remaining topic branches by ancestry, and emits the commands laptop should run for final integration.

It is plan-only. It does not checkout, merge, push, or delete branches.

## Current Merge Order

Current remote topic branches are ordered as:

```text
origin/codex/factor-batch-cn-stock-benchmark-relative-20260704
origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704
```

The first branch is an ancestor of the second branch. Merging in this order keeps the Round464 rejection evidence reviewable before absorbing the larger Round465-Round486 branch.

## Laptop Command Sequence

The plan emits this high-level sequence for laptop/project_sync on `main`:

```powershell
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git merge --no-ff -m "Merge origin/codex/factor-batch-cn-stock-benchmark-relative-20260704 for project sync" origin/codex/factor-batch-cn-stock-benchmark-relative-20260704
git merge --no-ff -m "Merge origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704 for project sync" origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
git push origin main
.\.venv\Scripts\python.exe scripts\sync_project.py --machine laptop --task project_sync --execute --cleanup-topic-branches
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha --execute
```

The final `pre-alpha` command is expected to keep blocking until paper-observation sufficiency reaches 20 fills.

## Office Desktop Result

Running the plan generator on office desktop with the current task context correctly reports:

```text
status=blocked
machine_must_be_laptop
task_must_be_project_sync
current_branch_must_be_main
working_tree_dirty
```

`working_tree_dirty` is transient while this Round486 change is uncommitted. The durable office-side blockers are the machine/task/branch ownership rules.

## Verification

TDD red check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_laptop_topic_integration_plan.py -q
```

Initial failure reason: `ModuleNotFoundError: No module named 'scripts.run_laptop_topic_integration_plan'`.

Green check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_laptop_topic_integration_plan.py -q
```

Result:

```text
3 passed
```

## Decision

Laptop now has an explicit machine-checkable path for the final branch/main cleanup. Office desktop remains responsible only for pushing this helper and continuing paper-observation or data-quality work when assigned.

Do not start `alpha-mine` until the laptop integration, remote branch cleanup, and observation sufficiency gates all clear.
