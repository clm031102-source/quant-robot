# Current Research And Cloud Sync Index

Last updated: 2026-06-27

Purpose: this is the first file to read after syncing the repository on any workstation. It records the current cloud structure, which branches are active, which branches must be preserved, and how to avoid repeating stale factor-mining directions.

## Current Cloud State

- Stable branch: `main`
- Current active CN stock sprint branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`
- Current sprint role: CN stock factor-validation and paper-simulation packaging evidence
- Current sprint status: pushed to GitHub, not merged into `main`
- Current sprint merge policy: review from laptop or integration branch before merging to `main`
- Live-trading boundary: disabled; research-to-paper only

## Branches To Keep

Keep these branches until the stated condition is met:

| Branch | Status | Keep Until |
| --- | --- | --- |
| `main` | stable branch | always |
| `codex/factor-validation-cn-stock-24h-profit-sprint-20260627` | active CN stock sprint evidence branch | merged into `main` or intentionally archived after laptop review |
| `codex/factor-batch-cn-etf-20260617` | pending CN ETF research branch | ETF material is reviewed and either integrated into `main` or explicitly archived in the branch integration manifest |

Do not delete `codex/factor-batch-cn-etf-20260617` as routine cleanup. It contains CN ETF data-sync, startup-gate, scheduler, factor, walk-forward, and test work that is relevant to the ETF-rotation project direction.

## Safe Branch Cleanup Rule

Merged topic branches may be removed from GitHub only when the safe-sync audit reports them as `merged_to_stable_branch`, `absorbed_by_manifest`, or `ignored_by_manifest`.

Use:

```powershell
python scripts\sync_project.py --machine <machine> --task <task> --execute --cleanup-topic-branches
```

Do not delete:

- `main`
- the current active sprint branch
- any branch listed under `research_branch_integration.pending`
- any branch that is not an ancestor of `origin/main` unless it is explicitly marked as ignored or absorbed in `configs/factor_branch_integration_manifest.json`

## Current CN Stock Paper Package

The current CN stock sprint produced a paper-simulation package, not a final promotable alpha.

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

## Multi-Workstation Rules

Laptop:

- Use for architecture, audits, branch integration, mainline merge decisions, and cloud cleanup review.
- Before reviewing current CN stock sprint work, fetch GitHub and inspect `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`.
- Before resuming ETF work, inspect `codex/factor-batch-cn-etf-20260617`.

Office desktop:

- Use for CN stock factor batches, validation reruns, and paper-package evidence.
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

1. Keep this index updated whenever a sprint branch is pushed or merged.
2. Clean remote branches that are already merged to `main`.
3. Preserve and separately review `codex/factor-batch-cn-etf-20260617`.
4. Merge or archive the current CN stock sprint branch after laptop review.
5. If docs keep growing, create dated sub-index pages rather than moving historical files and breaking existing config references.
