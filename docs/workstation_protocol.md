# Workstation Protocol

This project can be worked on from a laptop, a high-spec desktop, and an office desktop. The machines are execution contexts; branches are named by work content.

Start new Codex conversations from `main` when practical. Pull the latest `main`, confirm the machine and task, then create or switch to the appropriate task branch before doing non-trivial work.

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

For non-trivial desktop ETF research work, also run the Quant PM startup gate:

```powershell
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task factor_batch --branch codex/factor-batch-20260618-daily-basic
```

This gate rereads the startup protocol, workstation policy, README, research-family scheduler config, and research-family stop-loss note. If it returns `blocked`, stop before data downloads or factor batches and fix the blocker first.

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

## Daily Sync

Use this phrase with Codex when you want the current computer to sync safe project work:

```text
同步项目
```

The safe-sync meaning is:

1. Fetch and prune GitHub refs.
2. Inspect the current branch, upstream sync, and changed files.
3. Classify changed paths into syncable, blocked, and ignored.
4. Audit topic branches before core sync. `research_branch_integration.pending` tracks unabsorbed factor/Tushare research branches. `topic_branch_integration.pending` tracks other unabsorbed remote `origin/codex/*` task branches. `topic_branch_integration.cleanup` lists merged or manifest-absorbed remote topic branches that can be deleted after review. `local_topic_branch_cleanup.cleanup` lists local `codex/*` branches already merged to `origin/main` and not currently checked out. `branch_discovery.errors` must be empty; if Git branch discovery fails, execute/push mode blocks sync rather than treating missing refs as no pending work.
5. Commit only syncable code/config/test/doc files.
6. Push the current task branch only when the machine, task, branch, validation, branch-integration audit, and safety checks are clear.
7. Stop and ask before pushing if anything is ambiguous or risky.

Audit mode:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_batch
```

Execute and push mode:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_batch --execute --push
```

Codex must stop and ask before pushing when:

- the machine is not confirmed
- the task type is not confirmed
- the current branch is `main` for non-`project_sync` work
- the branch is behind upstream
- validation failed
- changed paths include data, logs, tokens, credentials, broker/account/order files, or other forbidden outputs

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

## Desktop Factor Validation

When a desktop is assigned stable framework validation, use task type `factor_validation` and run the residual-regime profile rather than starting a new exploratory batch:

```powershell
python scripts\run_desktop_factor_validation.py
```

This runs `configs/walk_forward_tushare_moneyflow_residual_regime.json` on local processed bars and Tushare moneyflow inputs. It allows zero accepted candidates because a clean rejection set is still useful evidence. It should still fail on train/test grid errors, missing data, or unsafe repository state.

Use the detailed checklist in `docs/research/desktop_residual_regime_validation_runbook_2026-06-16.md`.

## Safety Boundary

The project is still research-to-paper only:

- no broker connection
- no live account reads
- no order placement
- no automatic live trading
- `TUSHARE_TOKEN` stays in local environment variables only
