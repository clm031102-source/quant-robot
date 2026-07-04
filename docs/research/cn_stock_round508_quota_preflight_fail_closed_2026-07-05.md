# CN Stock Round508 Quota Preflight Fail-Closed CLI

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 5 after the Round504 review-agent baseline. This round hardened the local analyst-report quota preflight so it can stop a command chain when the preflight blocks a Tushare `report_rc` request.

## Round Objective

Round507 added a local preflight, but the CLI always exited `0` after printing JSON. That was useful for human review, but not fail-closed enough for a copy-pasted command sequence. Round508 added an explicit opt-in guard:

- Default CLI behavior remains unchanged.
- New flag: `--fail-on-blocked`.
- When the preflight decision is blocked and the flag is present, the CLI prints the JSON packet and exits with code `3`.
- When the preflight allows the request, the CLI exits `0`.

## Test-First Evidence

The new failing test was added before implementation:

```text
AssertionError: 2 != 3
```

This confirmed the flag was not implemented; argparse returned `2` for an unknown argument.

After adding the minimal CLI behavior:

```text
5 passed in 0.24s
```

## Startup And Data Evidence

Fresh 2026-07-05 gates:

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
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --target-date 2026-07-05 --max-daily-requests 2 --output-dir data\reports\round508_analyst_report_quota_preflight_20260705 --fail-on-blocked
```

Result:

- Status: `blocked`
- Request allowed: false
- Blockers: `daily_provider_request_budget_exhausted`
- Counted provider request windows: 2
- Remaining request windows: 0
- Exit code: `3`

The command did not call Tushare. It read local `data/reports` cache reports and wrote ignored preflight evidence under `data/reports`.

## Decision

Future analyst-report cache command chains should use `--fail-on-blocked` before any `report_rc` fetch. This makes the safe path mechanical:

1. Run startup gates.
2. Run quota preflight with `--fail-on-blocked`.
3. Continue to April cache only if preflight exits `0`.
4. Stop if preflight exits `3`.

Do not attempt the April 2024 `report_rc` cache on 2026-07-05.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
