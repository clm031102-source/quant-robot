# CN Stock Round511 Cache CLI Skip Quota Audit

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 8 after the Round504 review-agent baseline. This round tightened the exceptional `--skip-quota-preflight` path added around the analyst-report cache CLI.

## Round Objective

Round510 made `scripts/run_tushare_analyst_report_cache.py` run local quota preflight by default before any Tushare `report_rc` cache request. It also left `--skip-quota-preflight` for exceptional offline or controlled cases.

Round511 reduced the operational risk of that override:

- `--skip-quota-preflight` now requires `--skip-quota-preflight-reason`.
- A missing reason fails during argument validation before cache execution.
- A supplied reason prints a JSON audit packet with `status="skipped"` before cache execution continues.
- The normal provider-backed path remains default preflight first, fail-closed on quota block.

## Test-First Evidence

Two tests were added before implementation using only local temporary cached data:

- Missing skip reason should fail before cache execution.
- Supplied skip reason should be printed before a local cached replay continues.

Before implementation:

```text
2 failed
AssertionError: 0 != 2
AssertionError: 2 != 0
```

After implementation:

```text
tests/unit/test_analyst_report_quota_preflight.py
8 passed in 1.96s
```

Final verification:

```text
scripts/run_checks.py --profile laptop-integration --execute
81 passed in 16.34s
```

The tests use a local `DatasetStore` cached April 2024 window so the skip-path checks do not call Tushare.

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
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round511_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round511_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-target-date 2026-07-05 --quota-output-dir data\reports\round511_cache_cli_quota_preflight_20260705
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

Keep `--skip-quota-preflight` only for exceptional offline or controlled local replay cases, and require a human-readable reason every time it is used. Normal provider-backed analyst-report cache attempts must let the cache CLI run its default quota preflight and must stop on exit code `3`.

Do not attempt the April 2024 analyst-report cache again on 2026-07-05.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
