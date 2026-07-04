# Round536 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 33 after the Round504 review-agent baseline.
- Latest cloud/main audit: Round535.
- Latest laptop integration rehearsal: Round536.
- Stable branch: `origin/main` at `af474d5a`.
- Active topic branch: `origin/codex/factor-batch-cn-stock-profit-mining-20260704` at `e7f12d7d`.
- Topic branch is 33 commits ahead of `origin/main` and 0 commits behind.
- Laptop integration plan status from the office topic branch: blocked by `current_branch_must_be_main`.
- Temporary merge rehearsal: clean `ort` merge with no conflicts.
- Temporary merged validation: `laptop-integration` passed with 101 tests, compile, project audit, and safety audit.
- Temporary worktree and temporary branch were removed after rehearsal.

## What This Means

The branch is mechanically ready for laptop-owned integration, but the integration has not happened yet.

Do not say `main` contains Round504-Round536 work until laptop actually runs the project-sync integration, pushes `main`, and the remote branch state confirms it.

## Laptop Integration Command

Run only from laptop on `main`:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

Expected guarded sequence:

- fetch/prune origin;
- checkout `main`;
- pull `origin/main` with `--ff-only`;
- merge `origin/codex/factor-batch-cn-stock-profit-mining-20260704` with `--no-ff`;
- run `scripts\run_checks.py --profile laptop-integration --execute`;
- push `main`;
- run `scripts\sync_project.py --machine laptop --task project_sync --execute --cleanup-topic-branches`;
- run `scripts\run_checks.py --profile pre-alpha --execute`.

## Before Laptop Execute

Recheck:

```powershell
git fetch --prune
git status --short --branch
git rev-list --left-right --count origin/main...origin/codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

Proceed only if:

- current branch is `main`;
- working tree is clean;
- plan status is `ready`;
- branch discovery errors are `[]`;
- merge order is expected;
- no generated `data/` output is tracked or staged.

## If More Topic Commits Are Added First

If the active topic branch advances beyond `e7f12d7d`, rerun:

- startup gates;
- cloud/main branch audit;
- laptop integration plan;
- temporary merge rehearsal;
- `laptop-integration` validation on the temporary merged result.

## Still Blocked In Research Lane

- analyst April cache execution;
- frozen January-April prescreen;
- LPR provider refresh without explicit provider approval;
- external-feed factor revival;
- portfolio grids;
- promotion gates;
- final-holdout reads.

## Round543 Reminder

Round543 is the next required two-agent checkpoint. If the loop continues on the topic branch instead of laptop integration, run the checkpoint before any new source-family or factor decision.
