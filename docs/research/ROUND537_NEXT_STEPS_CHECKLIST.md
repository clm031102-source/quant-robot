# Round537 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 34 after the Round504 review-agent baseline.
- Latest cloud/main audit: Round535.
- Latest laptop integration rehearsal: Round537.
- Stable branch: `origin/main` at `af474d5a`.
- Active topic branch: `origin/codex/factor-batch-cn-stock-profit-mining-20260704` at `709bfe23`.
- Topic branch is 34 commits ahead of `origin/main` and 0 commits behind.
- Laptop integration plan from office topic branch remains blocked by `current_branch_must_be_main`.
- Round537 temporary merge rehearsal completed with no conflicts.
- Round537 temporary merged validation passed `laptop-integration` with 101 tests, compile, project audit, and safety audit.
- Temporary worktree and temporary branch were removed after rehearsal.

## Integration Meaning

The latest topic branch head is mechanically ready for laptop-owned integration. It is not yet integrated into `main`.

Do not claim `main` contains Round504-Round537 work until laptop actually merges, validates, pushes `main`, and remote branch state confirms the merge.

## Laptop Execution Command

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

## If Continuing On Office Desktop

Continue only non-provider work unless a prerequisite changes:

- import real quota packs from `highspec_desktop` and `laptop`;
- wait for local quota date change and run exactly one actual-date analyst quota preflight;
- prepare more integration or operator documentation;
- harden tests or source-tooling guardrails.

Do not push `main` or delete the active remote topic branch from office desktop.

## Research Blocks

Still blocked:

- analyst April cache execution;
- frozen January-April prescreen;
- LPR provider refresh without explicit provider approval;
- external-feed factor revival;
- portfolio grids;
- promotion gates;
- final-holdout reads.

## If Topic Advances Again

If the active topic branch advances beyond `709bfe23`, rerun:

- startup gates;
- laptop integration plan;
- temporary merge rehearsal from `origin/main`;
- `laptop-integration` verification on the temporary merged result;
- cleanup of temporary worktree and branch.

## Round543 Reminder

Round543 is the next required two-agent checkpoint. If the loop continues on the topic branch instead of laptop integration, run the checkpoint before any new source-family or factor decision.
