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

Branch names are task-based, not machine-based. Multiple desktops may run factor work at the same time, but they should use separate topic/date branches such as:

- `codex/factor-batch-<topic-or-date>`
- `codex/factor-validation-<topic-or-date>`
- `codex/factor-integration-<topic-or-date>`

Keep `main` stable. Do not run exploratory factor development directly on `main`.

GitHub is for code, configs, tests, lightweight summaries, and documentation. Do not commit `data/raw/`, `data/processed/`, `data/reports/`, large Parquet/CSV outputs, logs, tokens, broker credentials, account data, or live-trading secrets.

The project remains research-to-paper only: no broker connection, no live account reads, no order placement, and no automatic live trading.
