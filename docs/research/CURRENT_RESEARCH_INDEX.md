# Current Research And Cloud Sync Index

Last updated: 2026-07-04

Purpose: this is the first file to read after syncing the repository on any workstation. It records the current cloud structure, which research material has been absorbed into `main`, and how to avoid repeating stale factor-mining directions.

## Current Cloud State

- Stable branch: `main`
- Remote HEAD: `origin/main`
- Current remote topic branches: none
- Remote branch cleanup status: complete
- Latest integrated cloud commit: `9451558b`
- Live-trading boundary: disabled; research-to-paper only
- Latest cloud audit report: `docs/research/cloud_project_audit_2026-06-27.md`

All durable code, configs, tests, and lightweight reports that were previously on cloud topic branches are now integrated into `main`. New non-trivial work should start from latest `main`, then create a task branch using the branch policy in `configs/workstations.json`.

## Branches To Keep

| Branch | Status | Keep Until |
| --- | --- | --- |
| `main` | stable branch | always |

Do not create long-lived remote topic branches for routine desktop factor batches. Push task branches only when they contain code/config/docs that need cross-machine review, and delete them after they are merged or explicitly archived.

## Deleted historical branches

These branches were merged or absorbed into `main` on 2026-06-27 and then deleted from GitHub:

| Branch | Final Role | Result |
| --- | --- | --- |
| `codex/factor-validation-cn-stock-24h-profit-sprint-20260627` | CN stock factor-validation and paper-simulation evidence | integrated into `main` |
| `codex/factor-batch-cn-etf-20260617` | CN ETF data-sync, startup-gate, scheduler, factor, walk-forward, and test work | integrated through `codex/factor-integration-cn-etf-20260627`, then deleted |
| `codex/factor-integration-cn-etf-20260627` | temporary integration branch for the CN ETF branch cleanup | integrated into `main`, then deleted |

If one of these names appears again as a remote branch, treat it as a regression unless there is a new dated integration plan explaining why it was recreated.

## Safe Branch Cleanup Rule

Merged topic branches may be removed from GitHub only when the safe-sync audit reports them as `merged_to_stable_branch`, `absorbed_by_manifest`, or `ignored_by_manifest`.

Use:

```powershell
python scripts\sync_project.py --machine laptop --task project_sync --execute --cleanup-topic-branches
```

Do not delete:

- `main`
- any branch listed under `research_branch_integration.pending`
- any branch that is not an ancestor of `origin/main` unless it is explicitly marked as ignored or absorbed in `configs/factor_branch_integration_manifest.json`

## Current CN Stock Paper Package

The latest CN stock sprint produced a paper-simulation package, not a final promotable alpha.

Primary docs:

- `docs/research/cn_stock_round460_462_three_round_audit_2026-06-27.md`
- `docs/research/cn_stock_round462_q20_ps_gt10_risk_repair_2026-06-27.md`
- `docs/research/cn_stock_profit_sprint_simulation_shortlist_runbook_2026-06-27.md`

Current paper lanes:

| Lane | Role | Status |
| --- | --- | --- |
| `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08` | default baseline | ready for paper observation |
| `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08` | high-return risk-repair diagnostic lane | ready for paper observation |

Promotion status:

- New independent alpha from Rounds 460-462: `0`
- New paper-ready observation lane from Rounds 460-462: `1`
- Final promotable/live alpha: `0`
- Final holdout: sealed

## Current CN Stock Factor-Mining Status

Latest same-day progress report:

- `docs/research/cn_stock_round463_analyst_report_revision_source_smoke_2026-07-04.md`

Round463 reopened the analyst report revision direction only as a source-smoke because it is an orthogonal PIT source. The result improved over Round453:

- `report_rc` returned 1,754 rows and 780 assets for January 2024.
- The February extension hit a provider frequency limit reported as 1 request/hour.
- PIT prescreen ran on the one-month cache with 4 candidates and 8 tests.
- Research leads: 0.
- Promotion allowed candidates: 0.

Decision: analyst report revision is usable enough to cache slowly, but not usable enough for a profitability claim. Do not tune formulas or run portfolio grids from the one-month source smoke.

## Current CN ETF Framework

The CN ETF branch material is now part of `main`. The integrated ETF framework includes:

- Tushare `fund_basic`, `fund_daily`, `etf_share_size`, and fund-portfolio paths
- CN ETF readiness gate and rotation membership checks
- CN ETF research-family scheduler and Quant PM startup gate
- ETF share-size, moneyflow-basket, theme-breadth, and technical extension factors
- Unit tests for ETF data readiness, Tushare ETF sync, ETF factor builders, project audit, and startup gate

Before material desktop ETF research work, run:

```powershell
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task factor_batch --branch <current-branch>
```

This gate must keep the primary research market as `CN_ETF` and must keep direct `CN` stock moneyflow selection as `auxiliary_only`.

## Multi-Workstation Rules

Laptop:

- Use for architecture, audits, branch integration, mainline merge decisions, and cloud cleanup review.
- `factor_integration` is assigned to the laptop so desktop factor machines do not accidentally merge research branches into `main`.

Office desktop:

- Use for CN stock factor batches, validation reruns, and data-quality checks.
- Do not run ETF rotation work here unless explicitly assigned.
- Do not continue q20 threshold tuning without a new orthogonal data source or a paper-simulation monitoring reason.

High-spec desktop:

- Use for heavy data pipeline, Tushare downloads, large factor batches, and heavier validation.
- Keep large generated data under local `data/` paths only.

## Repository Hygiene Rules

GitHub may contain:

- source code
- tests
- configs
- lightweight Markdown summaries
- runbooks and index docs

GitHub must not contain:

- `data/raw/`
- `data/processed/`
- `data/reports/`
- large Parquet/CSV generated outputs
- logs
- Tushare token
- broker credentials
- account data
- order data
- live-trading secrets

## Current Cleanup Priorities

1. Keep this index updated whenever a sprint branch is pushed, merged, or deleted.
2. Keep `origin/main` as the only durable cloud branch unless active cross-machine review requires a temporary topic branch.
3. Run `python scripts\sync_project.py --machine laptop --task project_sync` after every branch cleanup.
4. If docs keep growing, create dated sub-index pages rather than moving historical files and breaking existing config references.
5. Treat recreated historical branch names as suspicious until their new purpose is documented.
