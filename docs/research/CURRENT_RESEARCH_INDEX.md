# Current Research And Cloud Sync Index

Last updated: 2026-07-05

Purpose: this is the first file to read after syncing the repository on any workstation. It records the current cloud structure, which research material has been absorbed into `main`, and how to avoid repeating stale factor-mining directions.

## Current Cloud State

- Stable branch: `main`
- Remote HEAD: `origin/main`
- Current remote topic branch: `codex/factor-batch-cn-stock-profit-mining-20260704`
- Remote branch cleanup status: Round464 and Round465-Round502 branches were merged into `main` and removed; keep only the active Round503/Round504 mining branch until it is reviewed or merged
- Latest integrated cloud commit: `af474d5a`
- Live-trading boundary: disabled; research-to-paper only
- Latest cloud audit report: `docs/research/cloud_project_audit_2026-06-27.md`

Read this file from top to bottom for current state, but treat dated Round sections before Round503 as historical evidence. Some older sections intentionally preserve the pre-cleanup blockers that were true when they were written.

All durable code, configs, tests, and lightweight reports that were previously on cloud topic branches are now integrated into `main`. New non-trivial work should start from latest `main`, then create a task branch using the branch policy in `configs/workstations.json`.

## Branches To Keep

| Branch | Status | Keep Until |
| --- | --- | --- |
| `main` | stable branch | always |

Do not create long-lived remote topic branches for routine desktop factor batches. Push task branches only when they contain code/config/docs that need cross-machine review, and delete them after they are merged or explicitly archived.

## Current Active Task Branch

| Branch | Role | Status |
| --- | --- | --- |
| `codex/factor-batch-cn-stock-profit-mining-20260704` | Round503 profit-mining startup evidence plus Round504-Round522 analyst-report-revision PIT source continuation, quota-aware review, local quota preflight, fail-closed CLI hardening, laptop-integration quota coverage, cache-CLI default quota preflight, skip-quota audit hardening, cache-CLI preflight-only mode, two-agent review/help hardening, quota-scope visibility, quota target-date guard, skip-quota offline replay guard, durable skip-quota audit evidence, cross-machine quota-pack evidence, quota-pack dedup hardening, duplicate-evidence audit details, quota-pack provenance metadata, and preflight-level pack provenance summaries | active research branch |

This branch is not a promotion branch. It records gated source construction, rejection evidence, and paper-lane risk-repair evidence. Do not treat any result on it as live, promoted, or independently tradable.

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
- `docs/research/project_round490_required_asset_end_retry_action_2026-07-04.md`
- `docs/research/project_round491_recent_refresh_next_action_evidence_2026-07-04.md`
- `docs/research/project_round492_observation_target_end_gap_plan_2026-07-04.md`
- `docs/research/project_round493_completion_gate_target_end_action_2026-07-04.md`
- `docs/research/project_round494_required_asset_target_end_check_2026-07-04.md`
- `docs/research/project_round495_latest_laptop_merge_rehearsal_2026-07-04.md`
- `docs/research/project_round496_laptop_integration_execute_mode_2026-07-04.md`
- `docs/research/project_round501_observation_sufficiency_cleared_2026-07-04.md`
- `docs/research/project_round501_completion_evidence_2026-07-04.json`
- `docs/research/project_round502_final_laptop_integration_rehearsal_2026-07-04.md`
- `docs/research/cn_stock_round518_cross_machine_quota_pack_2026-07-05.md`
- `docs/research/ROUND518_NEXT_STEPS_CHECKLIST.md`
- `docs/research/cn_stock_round519_quota_pack_dedup_2026-07-05.md`
- `docs/research/ROUND519_NEXT_STEPS_CHECKLIST.md`
- `docs/research/cn_stock_round520_quota_duplicate_details_2026-07-05.md`
- `docs/research/ROUND520_NEXT_STEPS_CHECKLIST.md`
- `docs/research/cn_stock_round521_quota_pack_provenance_2026-07-05.md`
- `docs/research/ROUND521_NEXT_STEPS_CHECKLIST.md`
- `docs/research/cn_stock_round522_quota_preflight_pack_provenance_2026-07-05.md`
- `docs/research/ROUND522_NEXT_STEPS_CHECKLIST.md`

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
- `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` is 37 commits ahead of `origin/main` after the Round502 final rehearsal evidence is pushed.
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

Round490 retried the after-gap latest execution-date window and hardened the next-action path:

- Real retry 2026-05-06 to 2026-07-03 still blocked because `CN_ETF_XSHE_160615` covered only 41 / 42 rows and stopped at 2026-07-02.
- Blockers remain `required_assets_not_covered`, `target_end_not_covered`, and `missing_date_rows`.
- `src/quant_robot/ops/recent_data_refresh.py` now emits `rerun_recent_refresh_to_latest_required_asset_end` when required assets cover the start but stop before the target end.
- The generated action points to the latest clean required-asset end date instead of repeating a known-bad target end.

Decision: continue retrying once `CN_ETF_XSHE_160615` covers 2026-07-03 or a later clean execution date. Do not start alpha mining.

Round491 regenerated the blocked recent-refresh evidence with the Round490 next-action code in place:

- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Real refresh 2026-05-06 to 2026-07-03 still blocked because `CN_ETF_XSHE_160615` covered only 41 / 42 rows and stopped at 2026-07-02.
- Processed rows: 84,380.
- Blockers remain `required_assets_not_covered`, `target_end_not_covered`, and `missing_date_rows`.
- The regenerated pack now emits `rerun_recent_refresh_to_latest_required_asset_end`.
- Generated command: `python scripts\run_recent_data_refresh.py --machine office_desktop --start-date 2026-05-06 --end-date 2026-07-02 --execute`.

Decision: do not rerun the known-clean 2026-05-06 to 2026-07-02 window just to reproduce existing evidence. Wait for `CN_ETF_XSHE_160615` to cover 2026-07-03 or a later clean execution date, then rerun the after-gap extension. Do not start alpha mining.

Round492 made the observation-continuation plan understand required-asset target-end gaps:

- Before the fix, the Round491 recent-refresh pack reported `gap_recovery.status=not_applicable` because there was no middle-window `required_asset_missing_trade_dates` split.
- The actual failure shape was `target_end_covered=false`: `CN_ETF_XSHE_160615` started at 2026-05-06 but stopped at 2026-07-02 before target end 2026-07-03.
- `scripts/run_observation_continuation_plan.py` now emits `gap_recovery.status=target_end_gap_available`.
- The generated recovery window is `latest_required_asset_clean_window`, 2026-05-06 to 2026-07-02.
- The generated action is `wait_for_required_asset_target_end`: wait for `CN_ETF_XSHE_160615` to cover 2026-07-03, or rerun only through the latest clean end 2026-07-02.

Decision: treat the active observation blocker as a provider target-end gap, not an open invitation to rerun the older 2026-03-23 to 2026-06-26 continuation window. Alpha mining remains blocked.

Round493 propagated the target-end gap into the project completion gate:

- Fresh Tushare check after Quant PM startup gate still found `160615.SZ` present on 2026-07-02 and missing on 2026-07-03.
- `scripts/run_project_completion_gate.py` now discovers the latest non-fixture recent-refresh pack.
- The gate records `recent_data_refresh.target_end_gap` when required assets stop before the requested target end.
- `pre-alpha` now emits `wait_for_required_asset_target_end` instead of a generic observation-continuation action when the Round491 pack is the active evidence.
- The action reports `CN_ETF_XSHE_160615`, target end 2026-07-03, latest clean end 2026-07-02, and the Round491 source pack.

Decision: keep alpha mining blocked. Recheck or refresh only when `160615.SZ` appears for 2026-07-03 or a later clean execution date; otherwise proceed with laptop-owned main integration and branch cleanup.

Round494 turned the target-end wait into an executable provider check:

- New script: `scripts/run_required_asset_target_end_check.py`.
- The script reads a recent-refresh pack, extracts required-asset target-end gaps, checks provider rows for the target end, and emits either `recheck_required_asset_target_end` or `run_recent_refresh_to_target_end`.
- `scripts/run_project_completion_gate.py` now points `wait_for_required_asset_target_end` to the new script.
- Real check after Quant PM startup gate: 2026-07-03 had 2,047 provider `fund_daily` rows, but `160615.SZ` still had 0 rows.
- Real status: `target_end_missing`.

Decision: do not rerun the after-gap refresh through 2026-07-03 until the target-end check reports `target_end_available`. Alpha mining remains blocked.

Round495 rehearsed the latest laptop-owned merge after Round494:

- Temporary isolated worktree: `C:\Users\Administrator\.config\superpowers\worktrees\lhjqr\integration-sim-round495-20260704`.
- Base: `origin/main @ 759c3cc3`.
- Merge order: Round464 branch first, then the Round465/Round494 branch.
- Both merges succeeded with no text conflicts.
- Simulated merged result vs `origin/main`: `0 34`, including 2 temporary merge commits plus 32 topic commits.
- Merged-result diff: 62 files changed, 7,976 insertions, 58 deletions.
- `scripts/run_checks.py --profile laptop-integration --execute` passed: 72 / 72 targeted tests, compile, project audit, and laptop `project_sync` audit.
- A completion-gate projection with `main`, no dirty paths, and no remaining topic branches leaves only `observation_sufficiency_not_cleared`.
- The temporary worktree and local simulation branch were removed after evidence collection.

Decision: the real laptop `project_sync` can proceed mechanically, but alpha mining remains blocked until observation sufficiency clears.

Round496 added guarded execute mode to the laptop integration plan:

- `scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute` now runs the emitted command sequence only when the plan status is `ready`.
- Blocked plans execute zero commands and exit 2.
- Final `pre-alpha` exit code 2 is accepted as expected evidence because observation sufficiency remains blocked after branch integration.
- Office-desktop safety check correctly refused execution on the current task branch with blockers `current_branch_must_be_main` and `working_tree_dirty`.

Decision: the laptop integration path is now both rehearsed and executable, but it must still run on laptop from `main`. Office desktop should not push `main` or delete remote topic branches.

Round501 cleared the observation sufficiency gate:

- Root cause: `鹏华沪深300ETF联接(LOF)-A` / `160615.SZ` was being classified as an ETF because the fund name contained `ETF`; it is now excluded when fund metadata contains `LOF`.
- `scripts/run_required_asset_target_end_check.py` now reports fund-basic metadata for required-asset target-end gaps and distinguishes non-current ETF assets from provider target-end waits.
- Recent-refresh coverage can ignore required assets that rotation membership structurally excludes with reasons such as `not_etf`.
- Round497 replay moved from stale/target-end blocked to fresh-data replay, then Round498 and Round500 widened the observation window.
- Round501 refreshed 2026-02-01 through 2026-07-03, replayed successfully, and produced `status=sufficient` with 25 observed fills versus 20 required.
- Default `pre-alpha` now discovers the Round501 sufficient pack and no longer emits `observation_sufficiency_not_cleared`.
- A tracked lightweight fallback evidence file, `docs/research/project_round501_completion_evidence_2026-07-04.json`, carries the same sufficiency summary so laptop/main integration does not depend on ignored office-local `data/reports` files.

Decision: the project is now 99% complete. Remaining blockers are only laptop-owned `main` integration, remote topic branch cleanup, and committing/pushing this Round501 evidence branch. Do not start alpha mining until the completion gate is clean on `main`.

Round502 rehearsed the final laptop integration after tracked completion evidence was added:

- Fresh isolated worktree from `origin/main @ 759c3cc3`.
- Merged Round464 then the latest Round465/Round501 branch with no conflicts.
- `scripts/run_checks.py --profile laptop-integration --execute` passed with 73 / 73 targeted tests.
- The simulated merged worktree had no `data/reports`, but completion gate still discovered `docs/research/project_round501_completion_evidence_2026-07-04.json`.
- A post-cleanup projection with branch `main`, no dirty paths, and no remote topic branches returned `status=complete`, `progress_estimate_percent=100`, and `factor_mining_allowed=true`.

Decision: laptop can now run `python scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute` from `main`. Office desktop should not push `main` or delete the remote topic branches.

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

## Round503 Main Cleanup And Profit-Mining Start

Round503 completed the user-authorized final cloud branch cleanup and started the next gated profit-mining branch:

- `main` now contains the Round464 benchmark-relative branch and the Round465-Round502 execution-aware branch.
- `scripts/run_checks.py --profile laptop-integration --execute` passed on merged `main`: 73 / 73 tests, compile, project audit, and laptop project-sync audit.
- `main` was pushed to GitHub at merge commit `af474d5a`.
- Project-sync cleanup removed the two absorbed topic branches locally and remotely.
- Final `pre-alpha` returned `status=complete`, `progress_estimate_percent=100`, `factor_mining_allowed=true`, and no blockers.
- New branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- CN stock factor-mining startup gate cleared on the new branch, and the CN stock data manifest had no blockers.
- Direct daily-basic alpha factory was blocked by the round-state validator, so the branch did not proceed with anonymous direct factor generation.
- Candidate plan gate cleared for the pre-registered Round465 paper-lane self-risk overlay candidate, with research screen allowed but portfolio grid and promotion disabled.
- A fixed self-risk overlay screen was run under `data/reports/round503_profit_mining_ps_gt10_self_risk_overlay_20260704`; the top candidate remained `ps_gt10_self_roll21_sum_m2_cash` with annualized return 0.08507982577628304, overlap-adjusted Sharpe 0.6969712816692145, and max drawdown -0.12458721638476855 versus baseline max drawdown -0.2542482236517434.

Decision: profit-mining has started only under the gated paper-risk-repair lane. This is not an independent alpha claim, promotion remains disabled, and the 2026 final holdout remains sealed. Next allowed paths are to resume the Round467 analyst-report-revision PIT source after the provider limit resets, register a genuinely new PIT source candidate plan, or continue paper-readiness hardening without q20/range/ps threshold tuning.

## Round504 Analyst Report PIT Continuation

Round504 continued the new PIT source path recommended by Round503 and by the two review agents:

- Quant PM startup gate passed on 2026-07-05 for `office_desktop` / `factor_batch`; primary market remains `CN_ETF`.
- CN stock factor-mining startup gate cleared on `codex/factor-batch-cn-stock-profit-mining-20260704`.
- CN stock data manifest had no blockers; warnings remain `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- `report_rc` February 2024 cache succeeded after the provider limit reset: 1,744 rows, 902 assets, 0 failed windows, 0 rate-limited windows.
- Frozen PIT prescreen used January plus February 2024 report roots, did not include final holdout, and covered 3,498 report rows / 1,317 report assets.
- Prescreen summary: 4 candidates, 8 tests, 6,882 factor rows, 13,764 aligned rows, 5 multiple-testing leads, 4 neutral-gate passes, 0 research leads, 0 promotion-allowed candidates.
- Main blocker for otherwise promising short-window statistics: `ic_year_coverage_below_gate`; this is expected because the source currently covers only one report year window.
- Next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`.

Docs:

- `docs/research/cn_stock_round504_analyst_report_revision_pit_continuation_2026-07-05.md`
- `docs/research/ROUND504_NEXT_STEPS_CHECKLIST.md`

Decision: do not promote or portfolio-grid analyst revision factors from the two-month smoke. The efficient next action is to cache the next monthly `report_rc` window after provider quota allows it, then rerun the same frozen prescreen. If the source still fails year-coverage or neutral gates after enough history, rotate to a genuinely new PIT source candidate plan.

## Round505 Analyst Report March Extension

Round505 continued the same frozen analyst-report-revision PIT source protocol:

- Quant PM startup gate passed for `office_desktop` / `factor_batch`; primary market remains `CN_ETF`.
- CN stock factor-mining startup gate cleared on `codex/factor-batch-cn-stock-profit-mining-20260704`.
- CN stock data manifest had no blockers; warnings remain `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- `report_rc` March 2024 cache succeeded: 1,634 rows, 531 assets, 0 failed windows, 0 rate-limited windows.
- Frozen PIT prescreen used January, February, and March 2024 report roots, did not include final holdout, and covered 5,132 report rows / 1,511 report assets.
- Prescreen summary: 4 candidates, 8 tests, 9,966 factor rows, 19,932 aligned rows, 0 multiple-testing leads, 2 neutral-gate passes, 0 research leads, 0 promotion-allowed candidates.
- Best remaining diagnostics were `analyst_np_revision_90` and `analyst_eps_revision_90` at horizon 20, with mean IC about 0.077 and ICIR about 0.56, but both failed FDR/multiple-testing and still failed year coverage.
- Next direction remains `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`.

Docs:

- `docs/research/cn_stock_round505_analyst_report_revision_march_extension_2026-07-05.md`
- `docs/research/ROUND505_NEXT_STEPS_CHECKLIST.md`

Decision: the third month weakened the short-window evidence instead of stabilizing it. Do not promote, portfolio-grid, or tune analyst revision formulas. The next efficient action is one more quota-aware monthly cache only if provider limits allow it; otherwise prepare a new PIT source candidate plan or a three-round direction review if the family keeps producing zero research leads.

## Round506 Analyst Report Quota-Aware Review

Round506 did not make a new Tushare request. It reviewed the local Round504/Round505 evidence because 2026-07-05 already had two successful monthly `report_rc` requests and Round467 documented a `2_per_day` provider limit.

- Quant PM startup gate passed for `office_desktop` / `factor_batch`; primary market remains `CN_ETF`.
- CN stock factor-mining startup gate cleared on `codex/factor-batch-cn-stock-profit-mining-20260704`.
- CN stock data manifest had no blockers; warnings remain `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Branch sync with upstream was `0 ahead / 0 behind`.
- Local evidence comparison: Round504 January-February had 5 multiple-testing leads, 4 neutral-gate passes, 0 research leads, and 0 promotion-allowed candidates.
- After adding March in Round505, multiple-testing leads fell to 0, neutral-gate passes fell to 2, research leads stayed 0, and promotion-allowed candidates stayed 0.
- Best mean IC fell from about 0.100 in Round504 to about 0.077 in Round505.

Docs:

- `docs/research/cn_stock_round506_analyst_report_revision_quota_aware_review_2026-07-05.md`
- `docs/research/ROUND506_NEXT_STEPS_CHECKLIST.md`

Decision: do not run a same-day third `report_rc` request, and do not tune analyst formulas. After quota reset, one April 2024 cache and the same frozen January-April prescreen are allowed. If January-April still has zero research leads or zero multiple-testing leads, run a family review and rotate to a new PIT source candidate plan.

## Round507 Analyst Report Quota Preflight

Round507 turned the Round506 manual quota decision into a local preflight tool before future `report_rc` requests:

- New module: `src/quant_robot/ops/analyst_report_quota_preflight.py`.
- New CLI: `scripts/run_analyst_report_quota_preflight.py`.
- New tests: `tests/unit/test_analyst_report_quota_preflight.py`.
- Focused unit test: 4 passed.
- Real local preflight for 2026-07-05 scanned `data/reports`, counted the Round504 February cache and Round505 March cache as 2 same-day provider request windows, and blocked a third same-day request with `daily_provider_request_budget_exhausted`.
- The preflight ignores resumed `cached` windows and reports from other dates, and blocks immediately when a same-day provider rate-limit row is observed.

Docs:

- `docs/research/cn_stock_round507_analyst_report_quota_preflight_2026-07-05.md`
- `docs/research/ROUND507_NEXT_STEPS_CHECKLIST.md`

Decision: run `scripts/run_analyst_report_quota_preflight.py` before every future analyst-report cache attempt. Only cache April 2024 after the preflight for the actual current date returns `request_allowed=true`.

## Round508 Quota Preflight Fail-Closed CLI

Round508 hardened the analyst-report quota preflight for command-chain use:

- `scripts/run_analyst_report_quota_preflight.py` now supports `--fail-on-blocked`.
- Default CLI behavior remains unchanged.
- With `--fail-on-blocked`, a blocked decision prints the JSON packet and exits `3`.
- Focused test: `tests/unit/test_analyst_report_quota_preflight.py` now covers this behavior, with 5 tests passing.
- Fresh gates passed on 2026-07-05: Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real local fail-closed preflight for 2026-07-05 blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.

Docs:

- `docs/research/cn_stock_round508_quota_preflight_fail_closed_2026-07-05.md`
- `docs/research/ROUND508_NEXT_STEPS_CHECKLIST.md`

Decision: future analyst-report cache command chains must run quota preflight with `--fail-on-blocked` before any `report_rc` fetch. Continue to April 2024 cache only if preflight exits `0`; stop if it exits `3`.

## Round509 Laptop Integration Quota Preflight Coverage

Round509 added the analyst-report quota preflight tests to the fixed laptop integration profile:

- `scripts/run_checks.py --profile laptop-integration --execute` now includes `tests/unit/test_analyst_report_quota_preflight.py`.
- The check-plan unit test was updated so future profile composition changes must keep this test file in the profile.
- Test-first evidence: the profile-composition test failed before implementation because the quota-preflight test file was missing from `LAPTOP_INTEGRATION_TESTS`.
- Focused verification passed: 6 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real local fail-closed preflight for 2026-07-05 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Full laptop integration verification passed with 78 tests, compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round509_laptop_integration_quota_preflight_coverage_2026-07-05.md`
- `docs/research/ROUND509_NEXT_STEPS_CHECKLIST.md`

Decision: keep quota-preflight tests in `laptop-integration` so sync and mainline checks catch regressions in the analyst-report request guard. Do not attempt the April 2024 analyst-report cache on 2026-07-05; continue only after an actual-date preflight exits `0`.

## Round510 Cache CLI Default Quota Preflight

Round510 moved analyst-report quota protection into the actual cache CLI entrypoint:

- `scripts/run_tushare_analyst_report_cache.py` now runs local quota preflight by default before any `report_rc` cache request.
- The cache CLI scans `data/reports` by default, accepts `--quota-report-root`, `--quota-output-dir`, `--quota-target-date`, and `--quota-max-daily-requests`, and exits `3` when preflight blocks.
- An explicit `--skip-quota-preflight` override exists for exceptional offline or controlled cases, but it is not allowed for normal provider-backed analyst-report fetches.
- Test-first evidence: the new cache-CLI test failed before implementation with return code `2` instead of expected `3`.
- Focused verification passed: `tests/unit/test_analyst_report_quota_preflight.py` now has 6 passing tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real cache-CLI fail-closed run for April 2024 on 2026-07-05 stopped at quota preflight, blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Full laptop integration verification passed with 79 tests, compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round510_cache_cli_default_quota_preflight_2026-07-05.md`
- `docs/research/ROUND510_NEXT_STEPS_CHECKLIST.md`

Decision: future analyst-report cache attempts should run the cache CLI directly and let its default quota preflight guard the provider request. Continue to April 2024 cache only after the cache CLI exits `0`; stop if it exits `3`.

## Round511 Cache CLI Skip Quota Audit

Round511 tightened the exceptional cache-CLI quota bypass path:

- `--skip-quota-preflight` now requires `--skip-quota-preflight-reason`.
- Missing skip reason fails during argument validation before cache execution.
- A supplied skip reason prints a JSON audit packet with `status="skipped"` before cache execution continues.
- Test-first evidence: the two new skip-path tests failed before implementation with `0 != 2` and `2 != 0`.
- Focused verification passed: `tests/unit/test_analyst_report_quota_preflight.py` now has 8 passing tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real cache-CLI fail-closed run for April 2024 on 2026-07-05 still stopped at quota preflight, blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Full laptop integration verification passed with 81 tests, compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round511_cache_cli_skip_quota_audit_2026-07-05.md`
- `docs/research/ROUND511_NEXT_STEPS_CHECKLIST.md`

Decision: keep `--skip-quota-preflight` only for exceptional offline or controlled local replay cases, and require a human-readable reason every time it is used. Normal provider-backed analyst-report cache attempts must use the default preflight and stop on exit code `3`.

## Round512 Cache CLI Preflight Only

Round512 added a safe cache-CLI quota dry-run mode:

- New flag: `--quota-preflight-only`.
- The cache CLI runs the same local quota preflight and writes the same preflight JSON/Markdown evidence.
- If preflight blocks, the CLI still exits `3`.
- If preflight allows, the CLI prints `status="preflight_only"` and exits `0` before cache execution.
- `--quota-preflight-only` cannot be combined with `--skip-quota-preflight`.
- Test-first evidence: the two new preflight-only tests failed before implementation with `2 != 0` and missing `cannot be combined` stderr.
- Focused verification passed: 11 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only run for April 2024 on 2026-07-05 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Controlled empty-report-root allowed-path run printed `status="preflight_only"`, exited `0`, and did not write a cache report.
- Full laptop integration verification passed with 83 tests, compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round512_cache_cli_preflight_only_2026-07-05.md`
- `docs/research/ROUND512_NEXT_STEPS_CHECKLIST.md`

Decision: use `--quota-preflight-only` when the team wants the cache CLI itself to prove quota readiness without consuming a provider request. Remove that flag only when intentionally starting the April 2024 cache after startup gates pass and actual-date preflight is allowed. Round513 should start with the required two-agent review checkpoint.

## Round513 Two-Agent Review And Cache CLI Help

Round513 completed the required round-10 review checkpoint after the Round504 baseline:

- Quant PM agent `Turing` recommended continuing only narrowly and conditionally: one April 2024 cache after actual-date `--quota-preflight-only` exits `0`, then rotate if January-April still has zero research leads or zero multiple-testing leads.
- Quant PM risks: evidence weakened after March, quota preflight is local-report based and can miss cross-machine same-day usage, and `--skip-quota-preflight` remains powerful.
- Ordinary-user agent `Maxwell` understood the safe path but found the dry-run and real cache commands too similar, CLI help under-explained, and `<date>` placeholders ambiguous.
- Round513 action: improved `scripts/run_tushare_analyst_report_cache.py --help` so quota-safe modes are self-explanatory.
- Test-first evidence: help-text test failed before implementation because `does not call Tushare` was missing.
- Focused verification passed: `tests/unit/test_analyst_report_quota_preflight.py` now has 11 passing tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only run for April 2024 on 2026-07-05 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Full laptop integration verification passed with 84 tests, compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round513_two_agent_review_and_cache_cli_help_2026-07-05.md`
- `docs/research/ROUND513_NEXT_STEPS_CHECKLIST.md`

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05. Next continuation should run the safe dry-run command first after quota plausibly resets, stop on exit `3`, and cache only if it exits `0`. Consider a cross-machine quota evidence plan before relying on local-only quota reports across multiple desktops.

## Round514 Quota Scope Visibility

Round514 addressed the Round513 Quant PM risk that quota preflight evidence was local-report based and could be mistaken for a global provider-quota guarantee:

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records `quota_scope="local_report_roots_only"` and `warnings=["local_report_roots_only"]`.
- The quota preflight summary records `report_root_count` and `report_roots`.
- The Markdown report now includes quota scope, warnings, and scanned report roots.
- The standalone preflight CLI and cache CLI both print quota scope and warnings in terminal JSON.
- Test-first evidence: the new scope tests failed first because the fields were missing, then the quota-preflight test file passed with 13 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, printed `quota_scope="local_report_roots_only"`, and returned exit code `3`.
- Full laptop integration verification passed with 86 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round514_quota_scope_visibility_2026-07-05.md`
- `docs/research/ROUND514_NEXT_STEPS_CHECKLIST.md`

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05. Future allowed preflight results must be read as "allowed within the scanned report roots"; include other workstation report roots with repeated `--quota-report-root` or manually confirm cross-machine provider usage before caching on shared quota days.

## Round515 Quota Target-Date Guard

Round515 closed a second cache-CLI safety gap: a nonlocal `--quota-target-date` could make quota preflight count the wrong local date before a provider-backed cache execution.

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records `summary.target_date_matches_generated_at`.
- The preflight warns with `quota_target_date_differs_from_generated_at` when target date differs from the local generated date.
- `scripts/run_tushare_analyst_report_cache.py` upgrades that warning to a blocker for provider-backed cache execution unless `--quota-preflight-only` is set.
- Cache CLI help now states that provider-backed cache requires the local generated date; nonlocal dates are for dry-run or audit evidence.
- Test-first evidence: the packet warning, cache CLI guard, and help assertion failed before implementation, then the quota-preflight test file passed with 15 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, reported `target_date_matches_generated_at=true`, and returned exit code `3`.
- Full laptop integration verification passed with 88 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round515_quota_target_date_guard_2026-07-05.md`
- `docs/research/ROUND515_NEXT_STEPS_CHECKLIST.md`

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05. Future provider-backed cache attempts should omit `--quota-target-date` or set it to the actual local generated date; nonlocal target dates are audit/dry-run only.

## Round516 Skip-Quota Offline Replay Guard

Round516 tightened the remaining strong quota bypass path:

- `scripts/run_tushare_analyst_report_cache.py` now checks requested processed analyst-report windows before honoring `--skip-quota-preflight`.
- Skip now requires cached processed windows for every requested `report_rc` window, with resume and processed writes enabled.
- If any requested window is missing, the CLI prints `status="blocked"`, includes `skip_quota_preflight_requires_cached_processed_windows`, and exits `3`.
- Successful skip packets include cached/missing processed-window counts and missing-window details.
- Help text now states that skip replay requires existing processed windows.
- Test-first evidence: the missing-cache skip test and help assertion failed before implementation, then the quota-preflight test file passed with 16 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- A real skip attempt with an empty processed-output directory blocked with `skip_quota_preflight_requires_cached_processed_windows` and returned exit code `3`.
- Full laptop integration verification passed with 89 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round516_skip_quota_offline_replay_guard_2026-07-05.md`
- `docs/research/ROUND516_NEXT_STEPS_CHECKLIST.md`

Decision: `--skip-quota-preflight` is now a local cached-replay path, not a provider-fetch bypass. Continue to April 2024 cache only after startup gates pass and the actual-date `--quota-preflight-only` exits `0`.

## Round517 Skip-Quota Durable Audit

Round517 made skip-quota attempts durable-audited beyond terminal output:

- `scripts/run_tushare_analyst_report_cache.py` now writes `skip_quota_preflight_audit.json` and `skip_quota_preflight_audit.md` before any skip path proceeds or exits.
- The skip audit records status, request decision, blocker list, cached/missing processed-window counts, missing-window details, skip reason, and safety text.
- Blocked skip attempts still exit `3` before cache execution.
- Test-first evidence: allowed and blocked skip tests failed first because audit files were missing, then the quota-preflight test file passed with 16 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- A real missing-cache skip attempt blocked with `skip_quota_preflight_requires_cached_processed_windows`, returned exit code `3`, and wrote durable skip-audit JSON/Markdown evidence.
- Full laptop integration verification passed with 89 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round517_skip_quota_durable_audit_2026-07-05.md`
- `docs/research/ROUND517_NEXT_STEPS_CHECKLIST.md`

Decision: skip-quota attempts are now both constrained and durable-audited. Normal provider-backed analyst-report cache still requires the default quota preflight and must stop on exit `3`.

## Round518 Cross-Machine Quota Pack

Round518 addressed the cross-machine quota evidence gap from Round517:

- Added `scripts/export_analyst_report_quota_pack.py` to export lightweight analyst-report cache summaries into a portable quota preflight root.
- Added `tests/unit/test_analyst_report_quota_pack.py` and wired it into the laptop integration profile.
- The exporter copies only valid `tushare_report_rc` cache-summary JSONs, writes JSON/Markdown manifests, excludes its own output directory, and refreshes its own `quota_report_roots/` on reruns.
- Analyst quota preflight now skips quota-pack internals during broad parent scans such as `data\reports`, while explicit scans of a pack root still count that pack evidence.
- Test-first evidence caught both issues: output-inside-root reruns counted `2` instead of `1`, and broad scans counted a pack copy plus the original until pack-aware scanning was added.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real pack export from `data\reports` wrote `data\reports\round518_analyst_quota_pack_20260705` with `exported_report_count=8`.
- Explicit pack preflight blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and exited `3`.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Full laptop integration verification passed with 91 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round518_cross_machine_quota_pack_2026-07-05.md`
- `docs/research/ROUND518_NEXT_STEPS_CHECKLIST.md`

Decision: use quota packs as cross-machine local evidence roots, not as a global provider-quota oracle. Future provider-backed analyst-report cache attempts should include every available workstation pack with repeated `--quota-report-root`, stop on exit `3`, and manually confirm same-day provider usage if any relevant pack is unavailable.

## Round519 Quota Pack Deduplication

Round519 hardened the Round518 quota-pack workflow after real export testing exposed copied-evidence duplication:

- `scripts/export_analyst_report_quota_pack.py` now writes a stable `quota_pack_source_fingerprint` into each exported cache-summary JSON.
- Export manifests record each report's source fingerprint.
- Exporter broad scans now skip old quota-pack internals, preventing new packs from recursively absorbing old pack copies.
- `src/quant_robot/ops/analyst_report_quota_preflight.py` now computes row-level quota evidence fingerprints and deduplicates repeated pack evidence.
- Preflight summary and Markdown now record `duplicate_evidence_rows`.
- Test-first evidence caught three cases: two packs exported from the same source counted as `2` instead of `1`; a local report plus its own pack counted as `2` instead of `1`; a broad export with an existing pack under the report root exported `2` instead of `1`.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Corrected real pack export from `data\reports` wrote `data\reports\round519_analyst_quota_pack_dedup_20260705` with `exported_report_count=8`.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and returned exit code `3`.
- Explicit preflight with `data\reports` plus the same Round519 pack twice still counted only 2 same-day provider request windows, skipped 2 duplicate evidence rows, blocked with `daily_provider_request_budget_exhausted`, and exited `3`.
- Full laptop integration verification passed with 94 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round519_quota_pack_dedup_2026-07-05.md`
- `docs/research/ROUND519_NEXT_STEPS_CHECKLIST.md`

Decision: quota packs are now safer to repeat in commands or copy across workstations because duplicate exported evidence no longer inflates same-day provider request counts. Normal provider-backed analyst-report cache remains blocked on 2026-07-05 and must wait for an actual-date preflight exit `0`.

## Round520 Quota Duplicate Evidence Details

Round520 made Round519 quota-pack deduplication auditable:

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records top-level `duplicate_window_rows`.
- Each duplicate row records the evidence fingerprint, kept report path, duplicate report path, generated date, window, status, quota-count flag, provider-rate-limit fields, and retry-after seconds.
- The Markdown preflight report now includes a `Duplicate Evidence Rows` table.
- Test-first evidence: the new assertion failed first with `KeyError: 'duplicate_window_rows'`, then quota-pack and quota-preflight focused tests passed.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Explicit preflight with `data\reports` plus the same Round519 pack twice still counted only 2 same-day provider request windows, skipped 2 duplicate evidence rows, wrote 2 duplicate detail rows, blocked with `daily_provider_request_budget_exhausted`, and exited `3`.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, had 0 duplicate evidence rows, and returned exit code `3`.
- Full laptop integration verification passed with 94 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round520_quota_duplicate_details_2026-07-05.md`
- `docs/research/ROUND520_NEXT_STEPS_CHECKLIST.md`

Decision: quota-pack deduplication is now visible enough for cross-machine review. Normal provider-backed analyst-report cache remains blocked on 2026-07-05 and must wait for an actual-date preflight exit `0`.

## Round521 Quota Pack Provenance

Round521 made quota packs self-describing for cross-machine review:

- `scripts/export_analyst_report_quota_pack.py` now accepts `--machine`, `--task`, and `--branch`.
- The pack manifest records `provenance.machine`, `provenance.task`, and `provenance.branch`.
- The Markdown manifest prints machine, task, and branch.
- The terminal JSON includes the same provenance object.
- Existing calls without these options still work and write empty provenance fields.
- Test-first evidence: the provenance test failed first because the exporter rejected `--machine`, `--task`, and `--branch`; after implementation, quota-pack and quota-preflight focused tests passed.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Real provenance-aware pack export wrote `data\reports\round521_analyst_quota_pack_provenance_20260705` with `exported_report_count=8`, machine `office_desktop`, task `factor_batch`, and branch `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Actual-date cache-CLI preflight-only for April 2024 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, had 0 duplicate evidence rows, and returned exit code `3`.
- Full laptop integration verification passed with 95 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round521_quota_pack_provenance_2026-07-05.md`
- `docs/research/ROUND521_NEXT_STEPS_CHECKLIST.md`

Decision: future cross-machine pack exports should include machine, task, and branch provenance. Normal provider-backed analyst-report cache remains blocked on 2026-07-05 and must wait for an actual-date preflight exit `0`.

## Round522 Quota Preflight Pack Provenance

Round522 lifted explicit quota-pack provenance into quota preflight evidence:

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now detects explicit quota-pack report roots and records top-level `quota_pack_provenance`.
- The preflight summary records `quota_pack_root_count`.
- The Markdown preflight report now includes a `Quota Pack Provenance` table.
- The standalone preflight CLI and cache CLI both print `quota_pack_provenance` in terminal JSON.
- Test-first evidence: the new preflight-provenance test failed first with `KeyError: 'quota_pack_root_count'`, then the focused pack and preflight tests passed.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Standalone preflight with `data\reports` plus `data\reports\round521_analyst_quota_pack_provenance_20260705` counted 2 same-day provider request windows, skipped 2 duplicate evidence rows, recorded `quota_pack_root_count=1`, surfaced the `office_desktop/factor_batch/codex/factor-batch-cn-stock-profit-mining-20260704` provenance, blocked with `daily_provider_request_budget_exhausted`, and exited `3`.
- Cache CLI preflight-only with the same roots printed the same pack provenance, blocked with `daily_provider_request_budget_exhausted`, and exited `3` before cache execution.
- Full laptop integration verification passed with 96 tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round522_quota_preflight_pack_provenance_2026-07-05.md`
- `docs/research/ROUND522_NEXT_STEPS_CHECKLIST.md`

Decision: future cross-machine quota reviews can inspect provenance directly from the preflight packet. Round523 is the next required two-agent checkpoint after the Round504 baseline. Normal provider-backed analyst-report cache remains blocked on 2026-07-05 and must wait for an actual-date preflight exit `0`.

## Round523 Two-Agent Quota Review

Round523 completed the required round-20 review checkpoint after the Round504 baseline:

- Quant PM reviewer `Gibbs` recommended waiting for quota reset and allowing only `--quota-preflight-only` dry-runs until actual-date preflight exits `0`.
- Ordinary-user reviewer `Heisenberg` found the safety path understandable but still too easy to misuse, especially startup gates, preflight exit codes, placeholders, cross-machine confirmation, and visually similar dry-run versus real-cache commands.
- Help hardening added clearer safety text to standalone preflight, cache CLI, and quota-pack exporter help.
- Test-first evidence: the new help tests failed first because the safety text was missing, then quota preflight and quota pack focused tests passed with 25 tests.
- Fresh gates passed on 2026-07-05: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Actual-date cache-CLI preflight-only for April 2024 with `data\reports` plus `data\reports\round521_analyst_quota_pack_provenance_20260705` still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, skipped 2 duplicate evidence rows, showed pack provenance, and returned `LASTEXITCODE=3`.
- Full laptop-integration verification passed with 98 unit tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round523_two_agent_quota_review_2026-07-05.md`
- `docs/research/ROUND523_NEXT_STEPS_CHECKLIST.md`

Decision: do not run provider-backed April cache on 2026-07-05. The next cache-related action is dry-run only after quota plausibly resets and after all workstation quota packs or manual same-day confirmations are accounted for. If April later caches and frozen January-April still has `research_lead_count=0`, run family review; if multiple-testing leads also remain `0`, rotate to a new PIT source plan.

## Round524 Quota Wait Checkpoint

Round524 followed the Round523 checklist with fresh gates and one safe cache-CLI dry-run:

- Startup context was clear and current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Quant PM startup gate returned `status="ready"` with blockers `[]`.
- CN stock factor-mining startup gate returned `status="cleared"` with blockers `[]`.
- CN stock data manifest returned blockers `[]` and warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Actual-date cache-CLI preflight-only for April 2024 with `data\reports` plus `data\reports\round521_analyst_quota_pack_provenance_20260705` still blocked with `daily_provider_request_budget_exhausted`.
- The dry-run counted 2 same-day provider request windows, skipped 2 duplicate evidence rows, showed `quota_pack_root_count=1`, kept `target_date_matches_generated_at=true`, showed the office-desktop pack provenance, and returned `LASTEXITCODE=3`.
- No provider-backed cache execution occurred.
- Full laptop-integration verification passed with 98 unit tests, Python compile, project audit, and laptop project-sync audit.

Docs:

- `docs/research/cn_stock_round524_quota_wait_checkpoint_2026-07-05.md`
- `docs/research/ROUND524_NEXT_STEPS_CHECKLIST.md`

Decision: do not run provider-backed April cache on 2026-07-05. If still on the same local quota day with no new cross-machine packs or manual same-day confirmations, avoid repeating the same dry-run; next useful work should collect missing workstation quota evidence, prepare the frozen January-April prescreen path without running it, or wait for the local quota date to change before one more actual-date dry-run.
