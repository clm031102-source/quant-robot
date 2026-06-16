# Agent Startup Protocol

This repository may be used from three machines:

- `laptop`
- `highspec_desktop`
- `office_desktop`

Before starting non-trivial work, ask the user to confirm:

1. Which machine is being used today.
2. What task type is being started.
3. Which branch should be used or created.
4. Whether commits and pushes are allowed for this task.

If the user already provided these answers, restate them briefly and continue.

Use `configs/workstations.json` as the source of truth for machine roles, task types, branch naming, data policy, and safety policy. Use `python scripts\start_task_context.py` to print the current startup context when orientation is needed.

New conversations should normally start from `main`. Pull latest `main`, confirm the machine and task, then create or switch to a task branch before non-trivial work. If the user already selected a task branch, verify it matches the requested task before editing.

Branch names are task-based, not machine-based. Multiple desktops may run factor work at the same time, but they should use separate topic/date branches such as:

- `codex/factor-batch-<topic-or-date>`
- `codex/factor-validation-<topic-or-date>`
- `codex/factor-integration-<topic-or-date>`

Keep `main` stable. Do not run exploratory factor development directly on `main`.

When a desktop machine is assigned stable `factor_validation` work for the residualized moneyflow/regime framework, prefer the pre-wired validation entrypoint:

```powershell
python scripts\run_checks.py --profile desktop-validation --execute
```

This profile runs safety checks, `scripts\run_desktop_factor_validation.py`, a CN data-quality audit against `data\processed` with output under `data\reports\data_quality_gap_audit_tushare_moneyflow_residual_regime`, a strict market-regime coverage check from walk-forward regime curves, the residual-regime promotion gate report, and a lightweight Markdown summary. The validation step uses `configs\walk_forward_tushare_moneyflow_residual_regime.json`; the promotion gate requires the market-regime coverage pack. A complete rejection set is acceptable evidence when the train/test grids complete; generated reports and processed data still stay out of Git.

GitHub is for code, configs, tests, lightweight summaries, and documentation. Do not commit `data/raw/`, `data/processed/`, `data/reports/`, large Parquet/CSV outputs, logs, tokens, broker credentials, account data, or live-trading secrets.

When the user says `同步项目`, treat it as a daily safe-sync request. Run `python scripts\sync_project.py --machine <machine> --task <task>` first to audit changed paths. If the machine, task, and branch are clear, changed paths are syncable, validation has passed, and there are no token/data/broker/account/order risks, use `python scripts\sync_project.py --machine <machine> --task <task> --execute --push` to commit and push the current task branch. Stop and ask the user before pushing when context is unclear, the current branch is `main` for non-`project_sync` work, the branch is behind upstream, validation failed, or forbidden paths are present.

The project remains research-to-paper only: no broker connection, no live account reads, no order placement, and no automatic live trading.
