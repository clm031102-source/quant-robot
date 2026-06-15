# Workstation Protocol

This project can be worked on from a laptop, a high-spec desktop, and an office desktop. The machines are execution contexts; branches are named by work content.

## Startup Questions

Before starting a task, confirm:

1. Which machine is being used.
2. What task type is being started.
3. Which branch should be used or created.
4. Whether commit and push are allowed.

Run this helper for a read-only context check:

```powershell
python scripts\start_task_context.py
```

With explicit context:

```powershell
python scripts\start_task_context.py --machine highspec_desktop --task factor_batch --branch codex/factor-batch-20260618-daily-basic
```

## Machines

- `laptop`: architecture, audits, docs, GitHub sync, merge work, and light smoke checks.
- `highspec_desktop`: data generation, large Tushare factor batches, and heavier validation.
- `office_desktop`: additional factor batches, validation reruns, and data-quality checks.

Two desktops may both work on factor research. They should not push unrelated work to the same branch at the same time.

## Branch Naming

Stable branch:

```text
main
```

Longer-lived task branches:

```text
codex/architecture-ops
codex/tushare-data-pipeline
codex/factor-mining-core
```

Short-lived topic/date branches:

```text
codex/factor-smoke-<topic-or-date>
codex/factor-batch-<topic-or-date>
codex/factor-validation-<topic-or-date>
codex/factor-review-<topic-or-date>
codex/factor-integration-<topic-or-date>
```

After a short-lived branch is merged and verified, delete it locally and remotely.

## Data Sync

GitHub syncs:

- source code
- tests
- configs
- lightweight summaries
- documentation

GitHub does not sync:

- `data/raw/`
- `data/processed/`
- `data/reports/`
- large Parquet/CSV outputs
- logs
- tokens or credentials

Use local copy, NAS, external drives, or a future DVC/object-storage workflow for large data.

## Safety Boundary

The project is still research-to-paper only:

- no broker connection
- no live account reads
- no order placement
- no automatic live trading
- `TUSHARE_TOKEN` stays in local environment variables only
