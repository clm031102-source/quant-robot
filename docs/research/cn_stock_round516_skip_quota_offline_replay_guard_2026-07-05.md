# Round516 Skip-Quota Offline Replay Guard

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round513 identified that `--skip-quota-preflight` was still powerful even after requiring a human-readable reason. Round516 tightens that path: skipping quota preflight is now only allowed when every requested analyst-report window already has a local processed cache partition, so the command can run as an offline cached replay.

This keeps the emergency/audit path available without letting it become a normal provider-backed fetch bypass.

## Changes

- `scripts/run_tushare_analyst_report_cache.py` now checks requested `report_rc` windows before honoring `--skip-quota-preflight`.
- The skip path requires `resume` and processed writes to remain enabled, because the ingest function only reuses cached windows under those settings.
- If any requested processed window is missing, the CLI prints `status="blocked"`, includes `skip_quota_preflight_requires_cached_processed_windows`, and exits `3`.
- Successful skip packets now include cached/missing processed-window counts and missing-window details.
- Help text now states that skip replay requires existing processed windows.

No provider-backed Tushare request was made in this round.

## Test-First Evidence

New tests were added before implementation:

- `test_cache_cli_skip_quota_preflight_blocks_when_cached_window_is_missing`
- Help text assertion for `requires existing processed windows`

The missing-cache test failed first because the existing command continued toward cache execution. The help assertion failed first because the requirement was not documented.

Focused verification after implementation:

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

Command: cache CLI with `--quota-preflight-only` for April 2024 and output under `data\reports\round516_cache_cli_quota_preflight_20260705`.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- `target_date_matches_generated_at`: `true`.
- Quota scope: `local_report_roots_only`.

Decision: do not run the April 2024 provider-backed analyst-report cache on 2026-07-05.

## Skip-Guard Evidence

Command: cache CLI with `--skip-quota-preflight --skip-quota-preflight-reason "offline cached replay"` but an empty processed-output directory.

Result:

- Exit code: `3`.
- Status: `blocked`.
- Blocker: `skip_quota_preflight_requires_cached_processed_windows`.
- Missing cached windows: `20240401..20240430`.
- Cache execution did not proceed.

## Decision

`--skip-quota-preflight` is now a local cached-replay path, not a provider-fetch bypass. For normal provider-backed cache, use the default quota preflight and stop on exit `3`.

Continue to April 2024 cache only after startup gates pass and the actual-date `--quota-preflight-only` exits `0`.
