# Phase 5.15 Paper Ops Runbook

Phase 5.15 turns the paper-ops guardrail into an ordered paper-only daily operations runbook.

It does not execute commands, download data by itself, connect to a broker, read accounts, place orders, or approve live trading. It writes the command queue that a human or future scheduler may run after reviewing the guardrail state.

## Command

```powershell
python scripts\run_paper_ops_runbook.py --paper-ops-guardrail data\reports\paper_ops_guardrail\paper_ops_guardrail_pack.json --output-dir data\reports\paper_ops_runbook
```

Outputs:

- `data/reports/paper_ops_runbook/paper_ops_runbook_pack.json`
- `data/reports/paper_ops_runbook/paper_ops_runbook_pack.md`
- `data/reports/paper_ops_runbook/paper_ops_runbook_commands.csv`

## Current Result

- stage: `phase_5_15_paper_ops_runbook`
- status: `paper_cycle_ready`
- paper cycle allowed: `true`
- live cycle allowed: `false`
- live readiness candidate: `false`
- guardrail status: `paper_ops_watch`
- command count: `4`
- warnings: `short_paper_history`, `provider_missing_date_rows`
- live boundary allowed: `false`

## Paper Command Queue

1. `check_tushare_readiness`
2. `run_tushare_activation_gate`
3. `update_paper_observation_history`
4. `update_paper_ops_guardrail`

Every command is marked `local_only=true`, `requires_manual_start=true`, and `live_boundary_allowed=false`.

## Decision Logic

The runbook writes the full paper cycle only when the guardrail allows continued paper observation. If the guardrail is blocked, the runbook writes only an inspection command and keeps `paper_cycle_allowed=false`.

Live cycle execution is always disabled in this phase.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase means the next paper-only operations commands are explicit and auditable. It is not permission to trade live.
