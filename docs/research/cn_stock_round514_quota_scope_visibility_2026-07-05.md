# Round514 Analyst Report Quota Scope Visibility

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round513 review identified a quota-risk ambiguity: the analyst-report quota preflight scans local report roots, so it cannot prove that no other workstation used the same provider quota window. Round514 keeps the fail-closed behavior unchanged and makes this scope explicit in the evidence packet and CLI output.

## Changes

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records `quota_scope="local_report_roots_only"` and a `local_report_roots_only` warning.
- The quota preflight summary now records `report_root_count` and `report_roots`.
- The Markdown evidence now includes `Quota scope`, `Warnings`, and `Report Roots`.
- `scripts/run_analyst_report_quota_preflight.py` prints quota scope and warnings in terminal JSON.
- `scripts/run_tushare_analyst_report_cache.py` prints the same quota scope and warnings before allowing, blocking, or dry-running the cache.

No provider request logic changed, and no Tushare request was made in this round.

## Test-First Evidence

New tests were added before implementation:

- `test_packet_records_scanned_report_roots_and_local_scope_warning`
- `test_standalone_cli_prints_quota_scope_warning`

Both failed first because `quota_scope` and printed warnings did not exist. After implementation, the focused quota-preflight test file passed with 13 tests.

Final verification before commit:

- Focused quota/check-plan tests: 14 passed.
- `scripts/run_checks.py --profile laptop-integration --execute`: 86 unit tests passed, Python compile passed, project audit passed, and laptop project-sync audit had no blockers.

## Protocol Evidence

- Startup context confirmed `office_desktop`, `factor_batch`, and the current branch.
- Quant PM startup gate status: `ready`, blockers `[]`.
- CN stock factor-mining startup gate status: `cleared`, blockers `[]`.
- CN stock data manifest status: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Actual-Date Dry Run

Command: cache CLI with `--quota-preflight-only` for April 2024 and `--quota-target-date 2026-07-05`.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- Quota scope: `local_report_roots_only`.
- Warning: `local_report_roots_only`.

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05.

## Decision

The cache guard is clearer but still intentionally local. Future cache attempts must treat an allowed preflight as "allowed within the scanned report roots", not as a global provider-quota guarantee across all workstations.

Before relying on a multi-machine day, either:

- include exported report roots from the other workstations with repeated `--quota-report-root`, or
- verify externally that no other workstation consumed the same `report_rc` provider budget.

Continue to April 2024 cache only after startup gates pass and the actual-date `--quota-preflight-only` exits `0`.
