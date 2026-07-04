# Current Research And Cloud Sync Index

Last updated: 2026-07-04

Purpose: this is the first file to read after syncing the repository on any workstation. It records the current cloud structure, which research material has been absorbed into `main`, and how to avoid repeating stale factor-mining directions.

## Current Cloud State

- Stable branch: `main`
- Remote HEAD: `origin/main`
- Current remote topic branches: `codex/factor-batch-cn-stock-benchmark-relative-20260704`; `codex/factor-batch-cn-stock-execution-aware-round465-20260704` after this task branch is pushed
- Remote branch cleanup status: pending for the two active topic branches
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
| `codex/factor-batch-cn-stock-execution-aware-round465-20260704` | Round465 fixed self-risk overlay check, Round466 strict paper-ops review, Round467 analyst-report retry-status evidence, Round470 final-holdout boundary evidence, Round471 financial/PIT source-gate refresh, Round472 paper replay refresh, Round473 expanded-observation data-quality block evidence, Round474 office-desktop completion handoff, Round475 fund-basic rotation-membership repair, Round476 live fund-basic membership guard, Round477 validated-ETF observation sufficiency evidence, Round478 latest validated-ETF observation update, Round479 laptop integration preflight, Round480 laptop integration profile plus latest target check, Round481 isolated laptop merge rehearsal, Round482 completion gate before profit mining, Round483 require-complete gate mode, Round484 latest observation-pack discovery, Round485 pre-alpha completion check profile, Round486 laptop topic integration plan, Round487 observation continuation/gate hardening, Round488 observation gap-recovery planning, and Round489 post-refresh window propagation | active review branch |

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
- `docs/research/project_round471_financial_pit_source_gate_refresh_2026-07-04.md`
- `docs/research/project_round472_post_refresh_replay_observation_refresh_2026-07-04.md`
- `docs/research/project_round473_expanded_observation_data_quality_block_2026-07-04.md`
- `docs/research/project_round474_office_desktop_completion_handoff_2026-07-04.md`
- `docs/research/project_round475_fund_basic_rotation_membership_repair_2026-07-04.md`
- `docs/research/project_round476_live_fund_basic_membership_guard_2026-07-04.md`
- `docs/research/project_round477_validated_etf_observation_sufficiency_2026-07-04.md`
- `docs/research/project_round478_latest_validated_etf_observation_update_2026-07-04.md`
- `docs/research/project_round479_laptop_integration_preflight_2026-07-04.md`
- `docs/research/project_round480_laptop_integration_profile_and_latest_target_check_2026-07-04.md`
- `docs/research/project_round481_isolated_laptop_merge_rehearsal_2026-07-04.md`
- `docs/research/project_round482_completion_gate_before_profit_mining_2026-07-04.md`
- `docs/research/project_round483_completion_gate_require_complete_2026-07-04.md`
- `docs/research/project_round484_completion_gate_latest_pack_discovery_2026-07-04.md`
- `docs/research/project_round485_pre_alpha_completion_check_profile_2026-07-04.md`
- `docs/research/project_round486_laptop_topic_integration_plan_2026-07-04.md`
- `docs/research/project_round487_observation_continuation_and_gate_hardening_2026-07-04.md`
- `docs/research/project_round488_observation_gap_recovery_plan_2026-07-04.md`
- `docs/research/project_round489_post_refresh_window_propagation_2026-07-04.md`

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
- `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` is 27 commits ahead of `origin/main` after Round489 is pushed.
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

Round471 refreshed the current financial/PIT source gate from all local `data/processed` financial statement and PIT signal roots:

- Financial/PIT source gate status: `blocked`.
- Source count: 112.
- Rows: 84,499.
- Unique symbols: 394 / 1,000 required.
- Candidate plan allowed: false.
- Blocker: `unique_symbol_count_below_minimum`.
- CN stock data manifest remained `review_required` with no blockers, but warnings still include `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Decision: do not generate financial/PIT candidates from the current 394-symbol cache. Continue this route only as source construction or retire it for the current sprint; do not use the cache for formula mining, portfolio grids, or promotion evidence.

Round472 reran the paper-only post-refresh replay from the ready recent-data refresh pack:

- Post-refresh replay reached Daily Ops and profile observation.
- Daily Ops status: `paper_ready`; paper trading allowed true; signal age 0 days; observed market `CN_ETF`; live boundary false.
- Daily Ops risk: total return 2.74%, max equity drawdown -0.17%, guard events 0, execution blocks 0.
- Profile observation blocker changed from `profile_observation_artifact_missing` to `minimum_fills_observed`.
- Observed fills: 6 / 20 required.
- Observation sufficiency status: `needs_more_observation_data`.
- Recommended expansion window: 2026-04-13 to 2026-07-01.
- Expanded observation dry run: `can_extend_observation_window=true`, but not cleared because the dry run did not execute the expanded data refresh.

Decision: paper-only observation may continue, but the candidate is not live-ready. The next real execution is an expanded recent-data refresh on the assigned ETF/paper workstation, followed by post-refresh replay and observation sufficiency recomputation.

Round473 executed the expanded recent-data refresh recommended by Round472:

- Quant PM startup gates for `data_pipeline` and `factor_review`: `ready`, blockers `[]`.
- Expanded refresh command used the Round472 profile-observation pack and target window 2026-04-13 to 2026-07-01.
- Tushare refresh executed and produced 107,598 processed rows across 2,065 CN ETF assets and 54 provider trade dates.
- Refresh status: `data_quality_blocked`.
- Required observed asset: `CN_ETF_XSHG_501222`.
- Required asset coverage: 37 / 54 expected rows, with 17 missing provider-calendar dates.
- Full-market raw rows were present on all 17 missing dates, but `501222.SH` was absent from every inspected raw partition.
- Longest complete suffix ending at 2026-07-01: 2026-06-30 to 2026-07-01, only 2 provider dates.
- Post-refresh replay status from the blocked refresh pack: `blocked`; Daily Ops and profile observation were not rerun.

Decision: do not bypass the required-asset data-quality gate, do not forward-fill the 17 missing rows, and do not claim observation sufficiency or live readiness from this expanded window. Next action is to verify suspension/no-trade or provider omission for `501222.SH`, continue real paper observation, or pre-register a replacement paper-observation workflow before changing the observed asset.

Round474 completed the office-desktop handoff:

- Current branch was synchronized with origin before the handoff.
- Relevant recent-data/replay/observation tests passed: 22 / 22.
- Sync audit for `office_desktop` / `factor_batch`: no blockers, no branch discovery errors, no blocked paths, and no syncable paths before the handoff document.
- Remote topic branches remain 2: Round464 is 1 commit ahead of `origin/main`; current Round465/467/473/474 branch is 12 commits ahead after this handoff is pushed.
- Round464 is an ancestor of the current branch.
- Laptop should perform `project_sync` / mainline integration and only then run safe topic-branch cleanup.

Decision: office_desktop should not merge `main` or delete remote branches. The next highest-value action is laptop integration. Profit-factor mining should wait until main is stable and the Round473 observation/data-quality lane is closed or explicitly re-scoped.

Round475 repaired the recent-refresh CN ETF rotation boundary:

- Root cause: `501222.SH` is listed in Tushare `fund_basic` as `易方达如意招享混合(FOF-LOF)-A`, with `is_etf=false`; it is not a valid CN ETF target.
- The prior recent-refresh membership writer marked every Tushare `fund_daily` asset as a rotation member, allowing this LOF/FOF fund into the paper replay.
- `scripts/run_recent_data_refresh.py` now loads Tushare `fund_basic` for live `tushare` recent refreshes and delegates membership construction to the formal `build_cn_etf_rotation_membership` logic.
- Regression test added: `test_fund_basic_rotation_membership_excludes_lof_from_recent_refresh`.
- Local ready recent-data membership after repair: 54,553 rows, 12,376 member rows, 1,559 member assets, source `tushare_fund_basic_fund_daily`.
- `CN_ETF_XSHG_501222` member rows after repair: 0.
- Post-repair replay selected `CN_ETF_XSHE_160615`, a fund-basic validated ETF member, not `501222`.
- Replay remains paper-only and blocked only by `minimum_fills_observed`.

Decision: do not backfill or forward-fill `501222.SH`; exclude it through fund-basic validated CN ETF membership. The project is cleaner, but not complete until laptop integrates the branch to `main`, safe-cleans the remote topic branches, and the paper-observation sufficiency route is rerun or re-scoped from the repaired replay evidence.

Round476 hardened the live recent-refresh failure path:

- Live `tushare` / `CN_ETF` recent refreshes now require fund-basic validated rotation membership.
- If live `fund_basic` is missing or empty, the refresh does not write permissive all-member rotation membership.
- The pack becomes `data_quality_blocked` with blocker `rotation_membership_fund_basic_missing`.
- Fixture refreshes keep the fixture fallback membership path for tests.
- Regression test added: `test_live_tushare_refresh_blocks_when_fund_basic_membership_cannot_be_validated`.
- Related recent/replay/observation tests passed: 25 / 25.

Decision: do not allow post-refresh replay to proceed from a live CN ETF recent refresh unless the rotation membership source is fund-basic validated. This prevents recurrence of the `501222.SH` non-ETF target leak under provider or token failures.

Round477 reran the paper-observation sufficiency path from the repaired fund-basic validated ETF target:

- Round475 baseline sufficiency after repair: 2 / 20 fills, deficit 18, suggested window 2026-04-03 to 2026-07-01.
- Recommended-window refresh for `CN_ETF_XSHE_160615`: blocked by one missing provider date, 2026-04-30.
- Continuous-window refresh 2026-05-06 to 2026-07-01: completed; required asset coverage 40 / 40, missing rows 0, duplicate rows 0, zero-volume rows 0.
- Rotation membership source remained `tushare_fund_basic_fund_daily`.
- Post-refresh replay selected `CN_ETF_XSHE_160615`, stayed paper-only, and had no execution blocks or guard events.
- Daily Ops risk on the continuous replay: total return 4.16%, max equity drawdown -0.80%.
- Final sufficiency: 5 / 20 fills, deficit 15, observation sufficiency not cleared.

Decision: the paper lane is valid and cleaner, but still sample-size blocked. Do not claim live readiness or factor promotion. Continue paper-only observation or explicitly re-scope the paper lane after laptop mainline integration.

Round478 extended the repaired fund-basic validated ETF replay to the latest clean Tushare date available for `CN_ETF_XSHE_160615`:

- Target availability check: 2026-07-01 and 2026-07-02 had `160615.SZ` rows; 2026-07-03 was an open calendar date but the target row was missing.
- Latest continuous refresh used 2026-05-06 to 2026-07-02 and completed with required asset coverage 41 / 41.
- Processed rows: 82,333.
- Rotation membership source remained `tushare_fund_basic_fund_daily`; member assets 1,559; member rows 33,758.
- Post-refresh replay stayed paper-only: Daily Ops `paper_ready`, live boundary false, no guard events, no execution blocks.
- Sufficiency remained blocked: 5 / 20 fills, deficit 15, additional observation estimate 72 days.

Decision: do not use 2026-07-03 for this observed ETF until the provider has a valid `160615.SZ` row or the paper lane is explicitly re-scoped. The latest clean extension did not change the blocker, so the next high-value work is still laptop-owned mainline integration, safe remote branch cleanup, and continued paper-only observation.

Round479 performed a non-destructive laptop integration preflight from the office desktop:

- `git fetch --all --prune` refreshed remote refs.
- `origin/codex/factor-batch-cn-stock-benchmark-relative-20260704` is 1 commit ahead of `origin/main`.
- `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` is 16 commits ahead before this Round479 preflight commit, and includes Round464 as an ancestor.
- `git merge-tree --write-tree` against `origin/main` returned clean tree hashes for both remaining topic branches.
- Current branch scope before Round479: 29 files changed, 3,557 insertions, 42 deletions.
- Laptop `project_sync` context confirmed the recommended branch is `main`.

Decision: the cloud integration is mechanically ready for laptop-owned execution. Merge Round464 first for review clarity, then merge the Round465/Round478/Round479 branch, rerun verification on merged `main`, push `main`, and only then run safe topic-branch cleanup. Office desktop should not mutate `main` or delete remote branches.

Round480 checked whether the repaired ETF target could be extended and added an executable laptop merged-main validation profile:

- Tushare `fund_daily` for 2026-07-03 returned 2,047 rows, but `160615.SZ` still had 0 rows.
- 2026-07-04 and 2026-07-06 had no usable target row.
- The latest clean target date remains 2026-07-02; do not extend the required target window to 2026-07-03.
- Added `scripts/run_checks.py --profile laptop-integration`.
- The profile runs targeted branch tests, `compileall`, project audit under ignored `data/reports/laptop_integration_project_audit`, and laptop `project_sync` safe-sync audit.

Decision: no additional observation bars can be safely added today. On laptop, after merging topic branches into `main`, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Then push `main` only if that profile and safe-sync audit pass.

Round481 rehearsed the laptop-owned merge in an isolated local worktree:

- Temporary worktree: `C:\Users\Administrator\.config\superpowers\worktrees\lhjqr\integration-sim-round481-20260704`.
- Temporary branch: `codex/integration-sim-round481-20260704`.
- Base: `origin/main`.
- Merge order: Round464 branch first, then the Round465/Round480 branch.
- Both merges succeeded with `ort`; no text conflicts.
- Simulated merged result vs `origin/main`: `0 20`, including two local merge commits plus 18 topic commits.
- Merged-result diff: 33 files changed, 3,913 insertions, 43 deletions.
- `scripts/run_checks.py --profile laptop-integration --execute` passed on the simulated merged result: 70 targeted tests passed, compile passed, project audit passed, laptop `project_sync` audit had no blockers and no branch-discovery errors.

Decision: the remaining mainline merge has now been rehearsed end to end without mutating `main` or remote branches. Laptop should perform the real merge and cleanup; office desktop should not delete the temporary remote topic branches or push `main`.

Round482 added a project completion gate before profit-factor mining:

- New script: `scripts/run_project_completion_gate.py`.
- New test: `tests/unit/test_project_completion_gate.py`.
- The gate checks current branch, stable branch, dirty worktree paths, remaining remote `origin/codex/*` topic branches, observation sufficiency status, and the research-to-paper safety boundary.
- Current real state reports `factor_mining_allowed=false`.
- Current blockers after this Round482 sync should be `not_on_stable_branch`, `remote_topic_branches_remaining`, and `observation_sufficiency_not_cleared`.
- Current observation evidence remains 5 / 20 fills with a 15-fill deficit.

Decision: before starting `alpha-mine`, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_project_completion_gate.py --observation-sufficiency-pack <latest_observation_sufficiency_pack>
```

Proceed only when `factor_mining_allowed=true`, `status=complete`, and `blockers=[]`.

Round483 hardened the completion gate for automation:

- `scripts/run_project_completion_gate.py --require-complete` now exits 2 when `factor_mining_allowed=false`.
- Without `--require-complete`, the gate remains a report command and exits 0 when it can emit JSON.
- Current clean office-desktop state still exits 2 with `--require-complete`.
- Current blockers remain `not_on_stable_branch`, `remote_topic_branches_remaining`, and `observation_sufficiency_not_cleared`.

Decision: any automated profit-factor mining entrypoint must run the require-complete gate first and stop on a nonzero exit code.

Round484 made the completion gate discover the latest observation sufficiency pack automatically:

- Default gate runs no longer require `--observation-sufficiency-pack`.
- Discovery skips fixture paths and targets known observation sufficiency pack locations instead of broad recursive scanning.
- Gate output now records `observation.source_path`.
- Current selected pack: `data\reports\round478_observation_sufficiency_validated_latest_20260704\observation_sufficiency_pack.json`.
- Current observation remains 5 / 20 fills, deficit 15, sufficiency not cleared.
- Local timing improved from about 2.55 seconds for broad recursive discovery to about 0.42 seconds with targeted discovery.

Decision: future completion checks can use:

```powershell
.\.venv\Scripts\python.exe scripts\run_project_completion_gate.py --require-complete
```

and the gate will use the latest non-fixture sufficiency evidence it can find.

Round485 added a `pre-alpha` completion check profile for automated mining safety:

- `scripts/run_checks.py --profile pre-alpha` now emits a single local `project_completion_gate` step.
- The step runs `scripts/run_project_completion_gate.py --require-complete`.
- `execute_check_plan` now preserves failed child exit codes, so the pre-alpha profile exits 2 when the completion gate blocks mining.
- Current blocked execution still reports `factor_mining_allowed=false`, selected Round478 sufficiency evidence, 5 / 20 fills, and a 15-fill deficit.
- During the uncommitted Round485 edit, `working_tree_dirty` appears as a transient blocker; after commit, the durable blockers remain `not_on_stable_branch`, `remote_topic_branches_remaining`, and `observation_sufficiency_not_cleared`.

Decision: run the pre-alpha profile before any future `alpha-mine` or profit-factor mining automation:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha --execute
```

Mining remains blocked until that profile exits 0 and the completion gate reports `factor_mining_allowed=true`, `status=complete`, and `blockers=[]`.

Round486 added a laptop-owned topic integration plan generator:

- New script: `scripts/run_laptop_topic_integration_plan.py`.
- New tests: `tests/unit/test_laptop_topic_integration_plan.py`.
- The script discovers `origin/codex/*` topic branches, skips branches already present in stable `main` or absorbed/ignored by `configs/factor_branch_integration_manifest.json`, orders remaining branches by ancestry, and emits the exact laptop command sequence.
- Current merge order remains Round464 first, then the current Round465-Round486 branch.
- On office desktop, the script correctly blocks because the machine/task/branch context is not laptop `project_sync` on `main`.

Decision: laptop should use:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

Then execute the emitted commands only when the plan is `status=ready`.

Round487 continued the paper-observation blocker path and hardened completion evidence selection:

- New script: `scripts/run_observation_continuation_plan.py`.
- New tests: `tests/unit/test_observation_continuation_plan.py`.
- The script emits a safe continuation plan: Quant PM startup gate, recent refresh, post-refresh replay, observation sufficiency, then `pre-alpha`.
- `scripts/run_recent_data_refresh.py` now catches ingest exceptions and writes a `data_quality_blocked` pack with blocker `ingest_failed` instead of losing provider empty-response failures as a traceback.
- Completion gate discovery now prefers repaired/validated observation evidence before sufficiency status, fills, and mtime. This keeps pre-repair Round472 6 / 20 and diagnostic Round487 1 / 20 packs from replacing the validated Round478 5 / 20 evidence.
- Real continuation attempt on 2026-03-23 to 2026-06-26 found one required-asset gap for `CN_ETF_XSHE_160615`: 2026-04-30.
- Pre-gap continuous refresh 2026-03-23 to 2026-04-29 passed with required asset coverage 27 / 27 and fund-basic validated membership, but replay still blocked with only 1 / 20 fills.

Decision: Round478 remains the current validated completion-gate observation source at 5 / 20 fills. Do not claim observation sufficiency from the pre-gap diagnostic segment.

Round488 converted the full-window observation data-quality gap into explicit recovery evidence:

- `src/quant_robot/data/quality_report.py` now records per-asset `missing_trade_dates`.
- `src/quant_robot/ops/recent_data_refresh.py` propagates required-asset missing trade dates into the recent-refresh pack.
- `scripts/run_observation_continuation_plan.py` accepts `--recent-data-refresh-pack` and emits `gap_recovery` windows plus complete per-window command sets.
- Full recommended retry 2026-03-23 to 2026-06-26 still blocks because `CN_ETF_XSHE_160615` is missing 2026-04-30.
- Post-gap continuous retry 2026-05-06 to 2026-06-26 passed required-asset coverage 37 / 37 and Daily Ops, but observation sufficiency remains 5 / 20 fills.

Decision: keep Round478 as the validated completion-gate source at 5 / 20. Use the gap-aware plan for targeted recovery; do not start alpha mining until `pre-alpha` clears.

Round489 traced why extending the post-gap data window did not increase observation fills:

- Root cause: `scripts/run_post_refresh_replay.py` did not pass the recent refresh target window into Daily Ops, and `scripts/run_daily_ops.py` did not pass `start_date` / `end_date` into the paper simulation.
- Fix: post-refresh replay now forwards the target window; Daily Ops now forwards `run_date` to signal snapshot `as_of_date` and `start_date` / `end_date` to paper simulation.
- Real clean retry 2026-05-06 to 2026-07-02 passed required asset coverage 41 / 41.
- Windowed replay now records `start_date=2026-05-06` and `end_date=2026-07-02` in the paper simulation request, but sufficiency remains 5 / 20.
- Extending to 2026-07-03 is blocked because `CN_ETF_XSHE_160615` is only covered through 2026-07-02.

Decision: wait for the required asset to cover 2026-07-03 or a later clean execution date, then rerun the after-gap extension. Do not start alpha mining.

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
