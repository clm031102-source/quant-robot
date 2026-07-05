# Round548 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 45 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round548.
- `handoff.blockers` mirrors the top-level blocker list.
- `handoff.blocker_count` records the blocker count.
- Handoff-only consumers can now explain `resolve_blockers` without reading the whole plan.

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
- `handoff.blockers=["current_branch_must_be_main"]`;
- `handoff.blocker_count=1`;
- `handoff.executable_here=false`;
- `handoff.recommended_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready`;
- `handoff.recommended_command_action=check_handoff_ready`;
- `handoff.next_command_allowed_here=false`.

From a dirty or otherwise blocked context:

- `handoff.status=blocked`;
- `handoff.blockers` lists all blockers;
- `handoff.blocker_count` matches that list length;
- `handoff.recommended_command=null`;
- `handoff.recommended_command_action=resolve_blockers`.

Only a true executable laptop/main plan should report:

- `handoff.blockers=[]`;
- `handoff.blocker_count=0`;
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
