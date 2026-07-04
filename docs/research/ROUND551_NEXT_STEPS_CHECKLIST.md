# Round551 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 48 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round551.
- `handoff.current_context_mismatch_reasons` now explains why the current context differs from laptop/project_sync/main.
- Branch-only mismatch can still be handoff-ready, but it is not executable here.

## Run Here First

On a clean office desktop topic branch, use the recommended command from JSON. It should be:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

This only checks handoff readiness.

## Do Not Run Here

Do not run this on office desktop:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

That command is laptop-only and requires `main`.

## Expected Handoff Fields

From a clean office topic branch planned for laptop project sync:

- `handoff.ready_for_handoff=true`;
- `handoff.current_context_matches_required=false`;
- `handoff.current_context_mismatch_reasons=["current_branch_must_be_main"]`;
- `handoff.executable_here=false`;
- `handoff.next_command_allowed_here=false`;
- `handoff.recommended_command_action=check_handoff_ready`.

Only a true executable laptop/main plan should report:

- `handoff.current_context_matches_required=true`;
- `handoff.current_context_mismatch_reasons=[]`;
- `handoff.executable_here=true`;
- `handoff.next_command_allowed_here=true`;
- `handoff.recommended_command_action=execute_integration`.

Wrong machine or wrong task contexts should report:

- `machine_must_be_laptop` when machine is not laptop;
- `task_must_be_project_sync` when task is not project_sync;
- `current_branch_must_be_main` when current branch is not main.

## Still Forbidden

- Tushare provider calls without cleared gates and explicit provider-use approval.
- Analyst April cache now.
- Frozen analyst prescreen now.
- LPR provider refresh now.
- External-feed factor tests.
- Portfolio grids.
- Promotion gates.
- Final-holdout reads.
- Office-desktop `main` push.
- Remote branch deletion from office desktop.
- Staging generated `data/` outputs.
