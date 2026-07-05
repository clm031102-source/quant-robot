# Round515 Analyst Report Quota Target-Date Guard

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round514 made quota scope explicit. Round515 closed the next operational safety gap: a user could set `--quota-target-date` to a nonlocal date, making the local same-day preflight look allowed even when the provider-backed cache would run on the actual local date.

This round keeps nonlocal target dates usable for audit and `--quota-preflight-only`, but provider-backed cache execution now fails closed when the quota target date differs from the local generated date.

## Changes

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records `summary.target_date_matches_generated_at`.
- The preflight adds `quota_target_date_differs_from_generated_at` to `warnings` when the target date is not the local generated date.
- `scripts/run_tushare_analyst_report_cache.py` upgrades that warning to a blocker for provider-backed cache execution unless `--quota-preflight-only` is set.
- Cache CLI help now states that provider-backed cache requires the local generated date; nonlocal dates are for dry-run or audit evidence.

No provider-backed Tushare request was made in this round.

## Test-First Evidence

New tests were added before implementation:

- `test_packet_warns_when_target_date_differs_from_generated_date`
- `test_cache_cli_blocks_provider_cache_when_quota_target_date_is_not_local_date`
- Help text assertion for the provider-backed local-date rule

The packet test failed first because `target_date_matches_generated_at` did not exist. The cache CLI test failed first because the command continued toward cache execution when the target date was nonlocal. The help assertion failed first because the local-date rule was not documented in `--help`.

Focused verification after implementation:

- `tests/unit/test_analyst_report_quota_preflight.py`: 15 passed.

Final verification before commit:

- Focused quota/check-plan tests: 16 passed.
- `scripts/run_checks.py --profile laptop-integration --execute`: 88 unit tests passed, Python compile passed, project audit passed, and laptop project-sync audit had no blockers.

## Protocol Evidence

- Startup context confirmed `office_desktop`, `factor_batch`, and the current branch.
- Quant PM startup gate status: `ready`, blockers `[]`.
- CN stock factor-mining startup gate status: `cleared`, blockers `[]`.
- CN stock data manifest status: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Actual-Date Dry Run

Command: cache CLI with `--quota-preflight-only` for April 2024, default local quota target date, and output under `data\reports\round515_cache_cli_quota_preflight_after_guard_20260705`.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- `target_date_matches_generated_at`: `true`.
- Quota scope: `local_report_roots_only`.

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05.

## Decision

The safe cache path now has two independent protections:

- same-day local report-root quota counting; and
- provider-backed cache execution must use the local generated quota date.

Future nonlocal `--quota-target-date` usage should be limited to audit evidence or `--quota-preflight-only`. For real cache execution, omit `--quota-target-date` or set it to the actual local date.
