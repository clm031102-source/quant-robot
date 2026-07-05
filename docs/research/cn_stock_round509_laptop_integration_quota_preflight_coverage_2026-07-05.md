# CN Stock Round509 Laptop Integration Quota Preflight Coverage

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 6 after the Round504 review-agent baseline. This round made the analyst-report quota preflight part of the fixed `laptop-integration` verification profile.

## Round Objective

Round507 and Round508 added the local analyst-report quota preflight and the `--fail-on-blocked` CLI behavior. The missing integration step was that `scripts/run_checks.py --profile laptop-integration --execute` still used the older fixed test list, so the new quota-preflight tests were not part of the main synchronization verification profile.

This round added `tests/unit/test_analyst_report_quota_preflight.py` to `LAPTOP_INTEGRATION_TESTS` and updated the check-plan assertion that guards the profile composition.

## Test-First Evidence

The profile-composition test was changed first to expect the quota-preflight test file. Before implementation it failed because the file was absent from the profile command:

```text
AssertionError: Lists differ
```

After adding the test file to `LAPTOP_INTEGRATION_TESTS`, focused verification passed:

```text
6 passed in 0.40s
```

## Startup And Data Evidence

Fresh 2026-07-05 gates:

- Startup context: `office_desktop`, `factor_batch`, branch `codex/factor-batch-cn-stock-profit-mining-20260704`, upstream sync `0	0`.
- Quant PM startup gate: `status=ready`, no blockers.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, no blockers.
- CN stock data manifest: no blockers, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Real Local Fail-Closed Preflight

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --target-date 2026-07-05 --max-daily-requests 2 --output-dir data\reports\round509_analyst_report_quota_preflight_20260705 --fail-on-blocked
```

Result:

- Status: `blocked`
- Request allowed: false
- Blockers: `daily_provider_request_budget_exhausted`
- Counted provider request windows: 2
- Remaining request windows: 0
- Exit code: `3`

The command did not call Tushare. It read local `data/reports` cache reports and wrote ignored preflight evidence under `data/reports`.

## Integration Evidence

Full laptop integration verification now includes the quota-preflight tests:

```text
scripts/run_checks.py --profile laptop-integration --execute
78 passed in 14.85s
```

The same profile also completed compile, project audit, and laptop project-sync audit. The project-sync audit listed only syncable code/test changes and no blockers.

## Decision

Keep quota-preflight tests inside `laptop-integration`. Future sync and mainline integration checks should catch regressions in the analyst-report request guard before another `report_rc` cache attempt is made.

Do not attempt the April 2024 analyst-report cache on 2026-07-05 because the fail-closed preflight still blocks the same-day third provider request.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
