# Round545 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 42 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round545.
- `handoff.here_command` is now present.
- `handoff.here_command` is the safe office-topic command.
- `handoff.next_command` remains laptop-only.

## Run Here First

On office desktop topic branch:

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
- `handoff.next_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`.

## Still Forbidden

- Tushare provider calls without cleared gates.
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
