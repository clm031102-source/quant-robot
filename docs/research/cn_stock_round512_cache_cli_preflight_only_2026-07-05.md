# CN Stock Round512 Cache CLI Preflight Only

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 9 after the Round504 review-agent baseline. This round added a cache-CLI dry-run mode for quota preflight.

## Round Objective

Round510 made `scripts/run_tushare_analyst_report_cache.py` run local quota preflight by default before any Tushare `report_rc` cache request. Round511 tightened the exceptional skip path.

The remaining operational gap was that, after a future quota reset, using the actual cache CLI to confirm quota readiness would immediately continue into the provider-backed cache request if preflight allowed it. Round512 added a safe stop point:

- New flag: `--quota-preflight-only`.
- The CLI runs the same local quota preflight and writes the same preflight JSON/Markdown evidence.
- If preflight blocks, the CLI still exits `3`.
- If preflight allows, the CLI prints `status="preflight_only"` and exits `0` before cache execution.
- `--quota-preflight-only` cannot be combined with `--skip-quota-preflight`.

## Test-First Evidence

Two tests were added before implementation:

- Allowed preflight-only should return `0`, print both `status="allowed"` and `status="preflight_only"`, and avoid writing a cache report.
- `--quota-preflight-only` combined with `--skip-quota-preflight` should fail argument validation.

Before implementation:

```text
2 failed
AssertionError: 2 != 0
AssertionError: 'cannot be combined' not found
```

After implementation:

```text
tests/unit/test_analyst_report_quota_preflight.py
10 passed in 2.86s
```

Focused profile verification:

```text
tests/unit/test_analyst_report_quota_preflight.py tests/unit/test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate
11 passed in 2.93s
```

Final verification:

```text
scripts/run_checks.py --profile laptop-integration --execute
83 passed in 17.19s
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

## Real Cache-CLI Evidence

Actual 2026-07-05 preflight-only run still blocked:

- Status: `blocked`
- Blockers: `daily_provider_request_budget_exhausted`
- Counted provider request windows: 2
- Exit code: `3`

Controlled allowed-path run used an empty local report root only to prove CLI behavior:

- Status: `allowed`
- Follow-up status: `preflight_only`
- Cache execution skipped: true
- Exit code: `0`
- No `tushare_analyst_report_cache.json` was written to the target cache output.

Neither command called Tushare.

## Decision

Use `--quota-preflight-only` when the team wants the cache CLI itself to prove quota readiness without consuming a provider request. Remove that flag only when intentionally starting the April 2024 cache after startup gates pass and preflight is allowed.

Do not attempt the April 2024 analyst-report cache again on 2026-07-05 because the actual-date preflight still exits `3`.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
