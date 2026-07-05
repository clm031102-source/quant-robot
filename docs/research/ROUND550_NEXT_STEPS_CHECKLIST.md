# Round550 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 47 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round550.
- `handoff.current_machine`, `handoff.current_task`, and `handoff.current_branch` now record the context used to build the plan.
- `handoff.current_context_matches_required` is true only for laptop/project_sync/main.

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

- `handoff.status=ready_on_main`;
- `handoff.ready_for_handoff=true`;
- `handoff.current_machine=laptop`;
- `handoff.current_task=project_sync`;
- `handoff.current_branch=codex/factor-batch-cn-stock-profit-mining-20260704`;
- `handoff.current_context_matches_required=false`;
- `handoff.required_machine=laptop`;
- `handoff.required_task=project_sync`;
- `handoff.required_branch=main`;
- `handoff.executable_here=false`;
- `handoff.next_command_allowed_here=false`;
- `handoff.recommended_command_action=check_handoff_ready`.

Only a true executable laptop/main plan should report:

- `handoff.current_machine=laptop`;
- `handoff.current_task=project_sync`;
- `handoff.current_branch=main`;
- `handoff.current_context_matches_required=true`;
- `handoff.executable_here=true`;
- `handoff.next_command_allowed_here=true`;
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
