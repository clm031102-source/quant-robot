# Round547 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 44 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round547.
- `handoff.recommended_command` now selects the safest copyable command for the current plan state.
- `handoff.recommended_command_action` explains what that command does.
- Ordinary blocked plans must use `recommended_command=null` and `recommended_command_action=resolve_blockers`.

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
- `handoff.executable_here=false`;
- `handoff.here_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready`;
- `handoff.next_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`;
- `handoff.next_command_context=laptop main only`;
- `handoff.next_command_allowed_here=false`;
- `handoff.recommended_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready`;
- `handoff.recommended_command_action=check_handoff_ready`.

Only a true executable laptop/main plan should report:

- `handoff.next_command_allowed_here=true`;
- `handoff.recommended_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`;
- `handoff.recommended_command_action=execute_integration`.

Any other blocked plan should report:

- `handoff.recommended_command=null`;
- `handoff.recommended_command_action=resolve_blockers`.

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
