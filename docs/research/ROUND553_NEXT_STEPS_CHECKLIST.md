# Round553 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 50 after the Round504 review-agent baseline.
- Latest checkpoint: Round553 two-agent handoff review.
- Quant PM reviewer verdict: no provider, factor, LPR, promotion, final-holdout, or further office hardening unless the handoff gate regresses.
- Ordinary-user reviewer verdict: the main remaining risk is copying the laptop-only `--execute` command from the office topic branch.
- The office topic branch is handoff-ready but not executable here.

## Safe Command Here

On a clean office desktop topic branch, this is the only integration-related command to run:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

It only checks handoff readiness.

## Laptop-Only Command

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

## Best Next Action

Move to laptop on `main`, rerun the laptop topic integration plan from the required context, and execute only if the plan is ready.

If work must continue on office desktop before laptop integration happens, do not add more handoff hardening by default. First rerun the safe handoff check and stop unless it regresses or the user explicitly redirects the work.

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
