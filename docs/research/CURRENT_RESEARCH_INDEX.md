# Current Research And Cloud Sync Index

Last updated: 2026-07-04

Purpose: this is the first file to read after syncing the repository on any workstation. It records the current cloud structure, which research material has been absorbed into `main`, and how to avoid repeating stale factor-mining directions.

## Current Cloud State

- Stable branch: `main`
- Remote HEAD: `origin/main`
- Current remote topic branches: `codex/factor-batch-cn-stock-benchmark-relative-20260704`; `codex/factor-batch-cn-stock-execution-aware-round465-20260704` after this task branch is pushed
- Remote branch cleanup status: complete
- Latest integrated cloud commit: `759c3cc3`
- Live-trading boundary: disabled; research-to-paper only
- Latest cloud audit report: `docs/research/cloud_project_audit_2026-06-27.md`

All durable code, configs, tests, and lightweight reports that were previously on cloud topic branches are now integrated into `main`. New non-trivial work should start from latest `main`, then create a task branch using the branch policy in `configs/workstations.json`.

## Branches To Keep

| Branch | Status | Keep Until |
| --- | --- | --- |
| `main` | stable branch | always |

Do not create long-lived remote topic branches for routine desktop factor batches. Push task branches only when they contain code/config/docs that need cross-machine review, and delete them after they are merged or explicitly archived.

## Current Active Task Branch

| Branch | Role | Status |
| --- | --- | --- |
| `codex/factor-batch-cn-stock-benchmark-relative-20260704` | Round464 benchmark-relative residual moneyflow pre-registration, walk-forward framework fixes, and rejection evidence | active review branch |
| `codex/factor-batch-cn-stock-execution-aware-round465-20260704` | Round465 fixed self-risk overlay check, Round466 strict paper-ops review, Round467 analyst-report retry-status evidence, and Round470 final-holdout boundary evidence | active review branch |

These branches are not promotion branches. They record a completed rejection set, framework fixes, and paper-lane risk-repair evidence that should be reviewed before integration.

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
- Final holdout: sealed for current lanes; historical Round145 read the holdout and then failed the result audit

## Current CN Stock Factor-Mining Status

Latest same-day progress reports:

- `docs/research/cn_stock_cloud_branch_integration_handoff_2026-07-04.md`
- `docs/research/cn_stock_round463_analyst_report_revision_source_smoke_2026-07-04.md`
- `docs/research/cn_stock_round464_benchmark_relative_moneyflow_preregistration_2026-07-04.md`
- `docs/research/cn_stock_round465_ps_gt10_self_risk_overlay_2026-07-04.md`
- `docs/research/cn_stock_round466_ps_gt10_self_risk_paper_ops_review_2026-07-04.md`
- `docs/research/cn_stock_round467_analyst_report_revision_retry_status_2026-07-04.md`
- `docs/research/project_round468_paper_ops_guardrail_runbook_status_2026-07-04.md`
- `docs/research/project_round469_readiness_blocker_audit_2026-07-04.md`
- `docs/research/project_round470_final_holdout_boundary_audit_2026-07-04.md`

Round463 reopened the analyst report revision direction only as a source-smoke because it is an orthogonal PIT source. The result improved over Round453:

- `report_rc` returned 1,754 rows and 780 assets for January 2024.
- The February extension hit a provider frequency limit reported as 1 request/hour.
- PIT prescreen ran on the one-month cache with 4 candidates and 8 tests.
- Research leads: 0.
- Promotion allowed candidates: 0.

Decision: analyst report revision is usable enough to cache slowly, but not usable enough for a profitability claim. Do not tune formulas or run portfolio grids from the one-month source smoke.

Round464 ran a frozen benchmark-relative residual moneyflow validation preflight:

- Candidate: `large_resid_liq_vol_amt_gate_20`
- Walk-forward config: `configs/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json`
- Candidate plan: `configs/factor_mining_candidate_plan_round464_benchmark_relative_moneyflow_20260704.json`
- Result: 6 cases, 4 folds, 0 accepted, 6 rejected.
- Best ranked case still had negative mean test relative return and failed adjusted IC significance.

Decision: do not promote this residual moneyflow candidate and do not continue it by tuning top-N, cost, or regime thresholds. Use Round464 as rejection evidence and rotate toward an orthogonal source or a pre-registered position-sizing/risk-construction idea.

Round465 tested fixed self-risk overlays on the already packaged Round462 `ps_gt10` paper lane:

- Candidate plan: `configs/factor_mining_candidate_plan_round465_ps_gt10_self_risk_overlay_20260704.json`
- Best overlay: `ps_gt10_self_roll21_sum_m2_cash`
- Baseline annualized / overlap Sharpe / max drawdown: 7.79% / 0.565 / -25.42%.
- Best overlay annualized / overlap Sharpe / max drawdown: 8.51% / 0.697 / -12.46%.
- Calendar walk-forward best fixed drawdown overlay: average test annualized 8.51%, average test overlap Sharpe 0.793, worst test drawdown -15.10%, strict pass rate 71.43%.

Initial decision: keep `ps_gt10_self_roll21_sum_m2_cash` as a stronger risk-repair candidate for follow-up review, not an independent alpha.

Round466 rebuilt strict paper-handoff and paper-ops review evidence for that overlay:

- Review config: `configs/cn_stock_profit_sprint_ps_gt10_self_risk_paper_ops_review_20260704.json`
- OOS split audit: 30 splits, mean OOS annualized 10.40%, mean OOS overlap Sharpe 0.906, worst OOS drawdown -12.46%, strict pass rate 63.33%.
- Cost-stress overlay: cost30 annualized 7.22%, overlap Sharpe 0.603, max drawdown -13.67%.
- Strict handoff review: 3 candidates, 2 ready, 1 blocked.
- Blocked overlay: `review_cohort_entry_timed_range_q20_m175_ps_gt10_self_roll21_m2_cash_cost10`
- Blockers: `not_paper_ready`, `oos_strict_pass_rate_below_min`.
- Paper ops package status remains `paper_ops_package_ready` with the existing Round462 `ps_gt10` high-return lane.

Decision: do not replace the Round462 `ps_gt10` high-return paper lane with the Round465 self-risk overlay under the current 0.75 OOS strict-pass gate. Keep the overlay only as blocked review evidence and rotate away from same-family q20/ps_gt10 repair unless a future pre-registered monitoring task requires it without retuning.

Round467 retried the orthogonal analyst-report-revision PIT source after Round463:

- Retry config: `configs/cn_stock_round467_analyst_report_revision_retry_plan_20260704.json`
- Attempted window: 2024-02-01 to 2024-02-29.
- Result: 0 fetched windows, 1 failed window, 0 rows, 0 assets.
- Provider limit: `report_rc` returned `2_per_day` with `retry_after_seconds` 86,400.
- Existing usable analyst-report cache remains Round463 January 2024 only: 1,754 rows and 780 assets.

Decision: do not burn more same-day `report_rc` retries. Resume February 2024 after the provider limit resets, then rerun the same frozen PIT prescreen with both January and February report roots. No formula tuning, portfolio grid, promotion gate, or final-holdout read is allowed for this source-smoke state.

Cloud branch integration handoff:

- `origin/codex/factor-batch-cn-stock-benchmark-relative-20260704` is 1 commit ahead of `origin/main`.
- `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` is 8 commits ahead of `origin/main` after Round470 is pushed.
- The Round464 branch is an ancestor of the Round465/467 branch, so laptop integration may merge Round464 first and then Round465/467 for review clarity, or merge Round465/467 once to absorb both.
- Do not delete either topic branch until laptop safe-sync marks it as merged or manifest-absorbed.

Round468 reran the paper-only operations guardrail and runbook from the existing paper observation history:

- Guardrail output: `data/reports/round468_paper_ops_guardrail_20260704`
- Runbook output: `data/reports/round468_paper_ops_runbook_20260704`
- Guardrail status: `paper_ops_watch`
- Runbook status: `paper_cycle_ready`
- Paper cycle allowed: true
- Live cycle allowed: false
- Live-readiness candidate: false
- Paper-ready history: 1 / 20 required runs
- Ready-run deficit: 19
- Provider missing date rows: 226
- Live boundary violations: 0

Decision: continue paper-only observation and provider-readiness refreshes. Do not make a live-readiness claim, do not connect to brokers or accounts, and do not treat the current paper history as factor promotion evidence.

Round469 reran the completion/readiness blocker audits:

- Quant PM startup gate: `ready`, blockers `[]`.
- CN stock factor-mining gate: `cleared`, next direction still `paper_simulation_packaging_or_new_pit_source_not_q20_threshold_tuning`.
- CN stock data manifest: no blockers; warnings remain `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Local readiness check: Tushare ready and parquet ready; no token or credential value was written to the repo.
- Readiness projection: 1 current blocker and 2 projected warnings.
- Blocker worklist: 1 open item, `manual_live_review_not_enabled`.
- Manual review rehearsal: blocked by `manual_live_review_not_enabled` and `manual_live_review_enabled_blocked`, with 5 of 7 requirements passing.
- Evidence refresh: data quality, provider readiness, paper observation, and duplicate resolution clear; manual review gate remains blocked.
- Observation sufficiency: blocked by `profile_observation_artifact_missing`; stale post-refresh replay should be rerun on the assigned paper/ETF workstation before recomputing sufficiency.

Decision: keep the live/manual review gate blocked by design under the research-to-paper boundary. Continue with laptop branch integration, assigned paper replay refresh, and non-hibernated PIT source work only.

Round470 revalidated the final-holdout boundary from the existing Round145 `daily_basic_free_float_supply_quality` report:

- Readiness audit: final holdout was truly read; bars reached 2026-06-15, signals reached 2026-05-28, and 6 holdout fold rows touched the final-holdout window.
- Result audit: 6 aggregate-accepted cases, 0 holdout-passed cases.
- Best holdout total return: -0.5949%.
- Best holdout overlap-adjusted Sharpe: -5.6965.
- Blocker: `no_case_passed_final_holdout_fold`.

Decision: historical Round145 is process evidence only and remains hibernated. Current Round464/Round465/Round467 lanes must not claim final-holdout passage, paper-gate clearance, or promotion readiness.

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
