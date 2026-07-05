# Round517 Skip-Quota Durable Audit

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round516 made `--skip-quota-preflight` a cached-replay-only path. Round517 made that path auditable beyond terminal output: every skip attempt now writes durable JSON and Markdown evidence under the cache output directory, whether the skip is allowed or blocked.

This helps later workstation users understand why a skip replay was permitted or refused without relying on console scrollback.

## Changes

- `scripts/run_tushare_analyst_report_cache.py` now writes `skip_quota_preflight_audit.json` and `skip_quota_preflight_audit.md` before any skip path proceeds or exits.
- The audit includes status, request decision, blocker list, cached/missing processed-window counts, missing-window details, skip reason, and safety text.
- Blocked skip attempts still exit `3` before cache execution.

No provider-backed Tushare request was made in this round.

## Test-First Evidence

Existing skip-path tests were extended before implementation:

- allowed cached replay must write `skip_quota_preflight_audit.json` and `.md`;
- blocked missing-cache replay must write the same durable audit files before exit `3`.

Both paths failed first because the audit files did not exist. After implementation:

- `tests/unit/test_analyst_report_quota_preflight.py`: 16 passed.

Final verification before commit:

- Focused quota/check-plan tests: 17 passed.
- `scripts/run_checks.py --profile laptop-integration --execute`: 89 unit tests passed, Python compile passed, project audit passed, and laptop project-sync audit had no blockers.

## Protocol Evidence

- Startup context confirmed `office_desktop`, `factor_batch`, and the current branch.
- Quant PM startup gate status: `ready`, blockers `[]`.
- CN stock factor-mining startup gate status: `cleared`, blockers `[]`.
- CN stock data manifest status: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Actual-Date Dry Run

Command: cache CLI with `--quota-preflight-only` for April 2024 and output under `data\reports\round517_cache_cli_quota_preflight_20260705`.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- `target_date_matches_generated_at`: `true`.
- Quota scope: `local_report_roots_only`.

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05.

## Skip-Audit Evidence

Command: cache CLI with `--skip-quota-preflight --skip-quota-preflight-reason "offline cached replay"` and an empty processed-output directory.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `skip_quota_preflight_requires_cached_processed_windows`.
- Missing cached windows: `20240401..20240430`.
- Durable audit files written under `data\reports\round517_skip_guard_missing_cache_20260705`.
- Cache execution did not proceed.

## Decision

Skip-quota attempts are now both constrained and durable-audited. Normal provider-backed analyst-report cache still requires the default quota preflight and must stop on exit `3`.

Continue to April 2024 cache only after startup gates pass and the actual-date `--quota-preflight-only` exits `0`.
