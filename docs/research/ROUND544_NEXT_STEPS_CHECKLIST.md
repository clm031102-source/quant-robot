# Round544 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 41 after the Round504 review-agent baseline.
- Latest handoff usability hardening: Round544.
- `handoff.executable_here` is now present.
- `ready_on_main` means handoff-ready only, not executable here.
- Office topic branch handoff should have `handoff.executable_here=false`.

## Office Handoff Check

From a clean office topic branch:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Then inspect:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

Expected:

- `status=blocked`;
- blocker is only `current_branch_must_be_main`;
- `handoff.status=ready_on_main`;
- `handoff.executable_here=false`;
- `handoff.status_description=handoff-ready only; rerun from laptop on main before executing`;
- `handoff.next_command` points to laptop `project_sync --execute`.

## Laptop Execution Rule

Only laptop on `main` may run:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

Do not execute this from office desktop.

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
