# Round540 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 37 after the Round504 review-agent baseline.
- Latest handoff-ready verification: Round540.
- Active topic branch head at verification time: `d427b61d`.
- Topic branch was 37 commits ahead of `origin/main` and 0 behind.
- `--require-handoff-ready` exited `0` from the clean office topic branch.
- Plan status remained `blocked` only by `current_branch_must_be_main`.
- `handoff.status=ready_on_main`.
- Merge order contained the active topic branch.

## Handoff Rule

For office-topic handoff, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Accept only exit code `0`.

If the command exits `2`, rerun without the require flag and inspect blockers.

## Execution Rule

Run real integration only from laptop on `main`:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

Do not push `main` or delete the active remote topic branch from office desktop.

## Do Not Repeat Manual Rehearsals By Default

Do not write another manual merge rehearsal document merely because a documentation commit advanced the topic branch.

Repeat a temporary merge rehearsal only if:

- integration plan code changes;
- topic branch gains code or config changes that could affect merge or validation;
- `--require-handoff-ready` stops passing;
- remote branch structure changes;
- laptop integration is about to execute and wants a fresh rehearsal.

## Research Blocks

Still blocked:

- analyst April cache execution;
- frozen January-April prescreen;
- LPR provider refresh without explicit provider approval;
- external-feed factor revival;
- portfolio grids;
- promotion gates;
- final-holdout reads.

## Round543 Reminder

Round543 is the next required two-agent checkpoint. If the loop continues on the topic branch instead of laptop integration, run the checkpoint before any new source-family or factor decision.
