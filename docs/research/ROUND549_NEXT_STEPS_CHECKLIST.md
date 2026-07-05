# Round549 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 46 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round549.
- `handoff.ready_for_handoff` is now the boolean readiness signal.
- `handoff.executable_here` and `handoff.next_command_allowed_here` still control whether execution is allowed in the current context.

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

From a clean office topic branch:

- `handoff.status=ready_on_main`;
- `handoff.ready_for_handoff=true`;
- `handoff.blockers=["current_branch_must_be_main"]`;
- `handoff.blocker_count=1`;
- `handoff.executable_here=false`;
- `handoff.recommended_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready`;
- `handoff.recommended_command_action=check_handoff_ready`;
- `handoff.next_command_allowed_here=false`.

From a dirty or otherwise blocked context:

- `handoff.status=blocked`;
- `handoff.ready_for_handoff=false`;
- `handoff.blockers` lists all blockers;
- `handoff.recommended_command=null`;
- `handoff.recommended_command_action=resolve_blockers`.

Only a true executable laptop/main plan should report:

- `handoff.status=ready`;
- `handoff.ready_for_handoff=true`;
- `handoff.executable_here=true`;
- `handoff.next_command_allowed_here=true`;
- `handoff.recommended_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`;
- `handoff.recommended_command_action=execute_integration`.

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
