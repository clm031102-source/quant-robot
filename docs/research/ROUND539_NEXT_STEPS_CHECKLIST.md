# Round539 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 36 after the Round504 review-agent baseline.
- Latest integration-plan tool hardening: Round539.
- `scripts\run_laptop_topic_integration_plan.py` now has `--require-handoff-ready`.
- `--require-handoff-ready` accepts a clean topic handoff with `handoff.status=ready_on_main`.
- `--require-handoff-ready` rejects dirty topic branches and other blockers with exit `2`.
- `--require-ready` remains reserved for true executable plans from laptop on `main`.

## Clean Topic Handoff Check

After Round539 is committed and pushed, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Expected from a clean office topic branch:

- exit code `0`;
- plan still has `status=blocked`;
- blocker list is `["current_branch_must_be_main"]`;
- `handoff.status=ready_on_main`;
- merge order contains the active topic branch.

If it exits `2`, inspect the plan JSON without the require flag.

## Laptop Execution Rule

Run only from laptop on `main`:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

Do not execute the plan from office desktop.

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
