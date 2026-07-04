# Round538 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 35 after the Round504 review-agent baseline.
- Latest integration rehearsal document: Round537.
- Latest integration-plan tool hardening: Round538.
- The laptop integration plan now emits `handoff` metadata.
- `handoff.status=ready_on_main` means the plan is blocked only because it is being viewed from a clean topic branch instead of `main`.
- Any additional blocker, including `working_tree_dirty`, keeps `handoff.status=blocked`.

## Clean Topic Handoff Check

After Round538 is committed and pushed, rerun:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

Expected from a clean office topic branch:

- `status=blocked`;
- `blockers=["current_branch_must_be_main"]`;
- `handoff.status=ready_on_main`;
- `handoff.required_machine=laptop`;
- `handoff.required_task=project_sync`;
- `handoff.required_branch=main`;
- `handoff.rerun_plan_before_execute=true`;
- merge order contains the active topic branch.

If `handoff.status=blocked`, inspect the extra blocker before any integration handoff.

## Laptop Execution Rule

Run only from laptop on `main`:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

Do not use an office-topic `ready_on_main` handoff as execution permission. It is a handoff signal only.

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
