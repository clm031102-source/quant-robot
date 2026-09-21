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

## Restricted Review Modes

The ordinary allocation criteria above do not describe every permitted review.
The implementation also recognizes explicit source-repair, preregistration,
single-prescreen, and family-rotation modes from the scheduler's `last_decision`.
These modes validate their own task scope and disabled boundaries; a `ready`
startup packet does not by itself permit factor generation.

As of 2026-09-21, the scheduler has no active primary allocation and the
consumed NAV prescreen is invalidated. `factor_review` is ready only in
`family_rotation_review_only` mode. `factor_batch`, walk-forward, promotion,
paper signals, and final holdout access remain disabled. Review the packet's
`safety` and `mode` fields before acting, and use the current
project virtual environment for commands.

## Blocked Means Stop

If the gate returns `blocked`, do not run Tushare downloads, factor batches, walk-forward validation, or paper-signal generation.
Fix the blocker first, then rerun the gate.
