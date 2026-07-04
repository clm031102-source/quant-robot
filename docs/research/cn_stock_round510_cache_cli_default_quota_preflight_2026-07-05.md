# CN Stock Round510 Cache CLI Default Quota Preflight

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 7 after the Round504 review-agent baseline. This round moved analyst-report quota protection into the actual Tushare `report_rc` cache CLI entrypoint.

## Round Objective

Round507 added a standalone local quota preflight. Round508 made that preflight fail closed when explicitly invoked. Round509 put the preflight tests into `laptop-integration`.

The remaining operational risk was that `scripts/run_tushare_analyst_report_cache.py` itself could still be copied and run without first calling the preflight command. Round510 changed the cache CLI so it runs local quota preflight by default before constructing the cache request.

## CLI Behavior

`scripts/run_tushare_analyst_report_cache.py` now:

- Runs local analyst-report quota preflight by default.
- Scans `data/reports` unless `--quota-report-root` is supplied.
- Writes quota preflight JSON/Markdown to `data/reports/analyst_report_quota_preflight` unless `--quota-output-dir` is supplied.
- Uses the current local date unless `--quota-target-date` is supplied.
- Uses the shared default max daily request budget unless `--quota-max-daily-requests` is supplied.
- Prints the quota decision before any cache request.
- Exits `3` when quota preflight blocks.
- Allows an explicit `--skip-quota-preflight` override for exceptional offline or controlled cases.

The underlying ingestion function was left unchanged; the safety gate is intentionally located at the human-facing command entrypoint.

## Test-First Evidence

The new cache-CLI test was added before implementation. It created two same-day local cache reports, then ran `scripts/run_tushare_analyst_report_cache.py` expecting fail-closed behavior before any fetch.

Before implementation the test failed because the cache CLI did not accept quota arguments:

```text
AssertionError: 2 != 3
```

After implementation:

```text
tests/unit/test_analyst_report_quota_preflight.py
6 passed in 0.73s
```

Final verification:

```text
scripts/run_checks.py --profile laptop-integration --execute
79 passed in 15.37s
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

## Real Cache-CLI Fail-Closed Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round510_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round510_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-target-date 2026-07-05 --quota-output-dir data\reports\round510_cache_cli_quota_preflight_20260705
```

Result:

- Status: `blocked`
- Request allowed: false
- Blockers: `daily_provider_request_budget_exhausted`
- Counted provider request windows: 2
- Remaining request windows: 0
- Exit code: `3`

The command stopped before calling Tushare. It only wrote ignored quota-preflight evidence under `data/reports`.

## Decision

Future analyst-report cache attempts should call `scripts/run_tushare_analyst_report_cache.py` directly with an appropriate `--quota-output-dir`; the CLI now performs the local quota preflight by default. Continue to April 2024 cache only after the cache CLI's default preflight allows the request and exits `0`.

Do not use `--skip-quota-preflight` for normal provider-backed `report_rc` fetches.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
