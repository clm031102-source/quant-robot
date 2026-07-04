# Round541 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 38 after the Round504 review-agent baseline.
- Latest integration handoff tool hardening: Round541.
- `handoff.next_command` is now included in the laptop integration plan.
- `handoff.next_command` points to laptop `project_sync --execute`.
- The command is guidance only; it must not be run from office desktop.

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
- blockers are only `current_branch_must_be_main`;
- `handoff.status=ready_on_main`;
- `handoff.next_command` is `python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`.

## Laptop Execution Rule

Run only from laptop on `main`:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

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
