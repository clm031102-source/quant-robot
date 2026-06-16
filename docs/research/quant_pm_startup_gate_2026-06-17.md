# Quant PM Startup Gate

This gate makes the project-manager review repeatable before any material factor work starts.
It is designed to prevent two recurring mistakes:

- Starting a factor batch without rereading the current project direction and workstation rules.
- Continuing a repeatedly failed research family instead of pivoting to the ETF rotation objective.

## Required Command

Before `data_pipeline`, `factor_batch`, `factor_validation`, or `factor_review` work on the desktop machines, run:

```powershell
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task factor_batch --branch <current-branch>
```

The gate reads and hashes:

- `AGENTS.md`
- `configs/workstations.json`
- `docs/workstation_protocol.md`
- `README.md`
- `configs/research_family_scheduler_cn_etf.json`
- `docs/research/research_family_scheduler_2026-06-17.md`
- `docs/research/quant_pm_startup_gate_2026-06-17.md`

## Pass Criteria

- Machine, task, and branch are explicit.
- The current branch matches the requested branch and is not `main` for non-sync work.
- The final research signal market is `CN_ETF`.
- The research-family scheduler is `ready`.
- Direct `CN` stock moneyflow selection remains `auxiliary_only` with zero budget.
- At least one primary `CN_ETF` research allocation exists.
- The live boundary remains disabled.

## Blocked Means Stop

If the gate returns `blocked`, do not run Tushare downloads, factor batches, walk-forward validation, or paper-signal generation.
Fix the blocker first, then rerun the gate.
