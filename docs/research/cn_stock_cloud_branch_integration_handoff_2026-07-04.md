# CN Stock Cloud Branch Integration Handoff

Date: 2026-07-04

Prepared on: office_desktop

Scope: cloud branch cleanup and mainline integration handoff for the current CN stock research branches. This document does not merge `main`; laptop remains the integration machine.

## Project Progress Snapshot

Estimated project completion: 93%.

Remaining before completion:

- Integrate the two active cloud review branches into `main` from laptop.
- Keep `main` stable, then delete merged topic branches only after the safe-sync audit marks them clean.
- Continue profitable-factor discovery only through orthogonal PIT sources or pre-registered paper-readiness hardening.
- Keep final-holdout data sealed until all long-cycle, OOS, cost, capacity, tail, regime, and multiple-testing gates clear.

## Current Remote State

| Branch | Commit | Relation to `origin/main` | Role |
| --- | --- | --- | --- |
| `origin/main` | `759c3cc3` | stable | latest integrated main |
| `origin/codex/factor-batch-cn-stock-benchmark-relative-20260704` | `ab744f9c` | 1 commit ahead of `origin/main` | Round464 benchmark-relative moneyflow rejection evidence |
| `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` | `44b99ae4` | 4 commits ahead of `origin/main` | Round465 self-risk overlay, Round466 paper-ops review, Round467 analyst-report retry status |

Important relation:

```text
origin/codex/factor-batch-cn-stock-benchmark-relative-20260704
is an ancestor of
origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704
```

So the Round465/467 branch is stacked on Round464.

## Suggested Laptop Integration Order

Preferred review-preserving path:

1. Start on laptop with `main`.
2. Pull latest `origin/main`.
3. Merge or review `origin/codex/factor-batch-cn-stock-benchmark-relative-20260704`.
4. Merge or review `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704`.
5. Run the verification checklist below.
6. Push `main`.
7. Run safe branch cleanup only after the branches are merged or manifest-absorbed.

Equivalent compact path:

- Merge `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704` once; this absorbs Round464 because the Round464 commit is already in its history.

Use the preferred path if a human wants separate review of Round464's walk-forward framework changes before the Round465/466/467 paper-lane evidence.

## What These Branches Add

Round464:

- `configs/factor_mining_candidate_plan_round464_benchmark_relative_moneyflow_20260704.json`
- `configs/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json`
- `docs/research/cn_stock_round464_benchmark_relative_moneyflow_preregistration_2026-07-04.md`
- Walk-forward framework fixes in `src/quant_robot/experiments/runner.py` and `src/quant_robot/validation/walk_forward.py`
- Related unit tests in `tests/unit/test_experiment_runner.py` and `tests/unit/test_walk_forward.py`

Decision: 6 benchmark-relative residual moneyflow cases were rejected. Do not promote or retune this family from Round464.

Round465/466/467:

- `configs/factor_mining_candidate_plan_round465_ps_gt10_self_risk_overlay_20260704.json`
- `configs/cn_stock_profit_sprint_ps_gt10_self_risk_paper_ops_review_20260704.json`
- `configs/cn_stock_round467_analyst_report_revision_retry_plan_20260704.json`
- `docs/research/cn_stock_round465_ps_gt10_self_risk_overlay_2026-07-04.md`
- `docs/research/cn_stock_round466_ps_gt10_self_risk_paper_ops_review_2026-07-04.md`
- `docs/research/cn_stock_round467_analyst_report_revision_retry_status_2026-07-04.md`

Decisions:

- Round465 self-risk overlay improved drawdown but failed the strict Round466 handoff replacement gate.
- Existing Round462 `ps_gt10` high-return lane remains the paper-observation lane.
- Round467 analyst-report-revision February 2024 retry was blocked by Tushare `report_rc` provider limit `2_per_day`; resume only after the limit resets.

## Verification Checklist For Laptop

After integration, run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_experiment_runner.py tests\unit\test_walk_forward.py tests\unit\test_simulation_shortlist_paper_handoff.py tests\unit\test_simulation_shortlist_paper_handoff_cli.py tests\unit\test_simulation_paper_ops_package.py tests\unit\test_shortlist_oos_split_audit.py tests\unit\test_shortlist_self_risk_overlay.py tests\unit\test_analyst_report_revision_prescreen.py -q
.\.venv\Scripts\python.exe -B -m compileall -q scripts src tests
.\.venv\Scripts\python.exe scripts\run_project_audit.py --output-dir data\reports\laptop_post_round467_integration_project_audit_20260704 --json
.\.venv\Scripts\python.exe scripts\sync_project.py --machine laptop --task project_sync
```

If the safe-sync audit is clean after merge and push:

```powershell
.\.venv\Scripts\python.exe scripts\sync_project.py --machine laptop --task project_sync --execute --cleanup-topic-branches
```

Do not delete either topic branch manually before the audit reports it as safe to clean.

## Post-Integration Research Direction

Use this order:

1. If the Tushare `report_rc` provider limit has reset, resume the Round467 February 2024 cache using `configs/cn_stock_round467_analyst_report_revision_retry_plan_20260704.json`.
2. If `report_rc` remains blocked, rotate to a genuinely different PIT source or a non-tuning paper-readiness audit.
3. Do not continue q20/`ps_gt10` threshold variants, benchmark-relative moneyflow tuning, financial-reporting-timeliness slow backfill inside the sprint, or one-month analyst-report formula tuning.

The project remains research-to-paper only: no broker connection, no live account reads, no order placement, and no automatic live trading.
