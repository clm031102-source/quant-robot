# Round518 Cross-Machine Analyst Quota Pack

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round518 addressed the remaining Round517 quota-risk item: local analyst-report quota preflight evidence is not a global provider-quota guarantee when multiple desktops share the same Tushare account.

This round adds a lightweight quota-pack exporter so a workstation can export its local `tushare_analyst_report_cache.json` summaries and another workstation can pass that exported directory as an additional `--quota-report-root`. The pack contains summary JSON evidence only. It does not export raw/processed market data, parquet files, tokens, broker credentials, account data, orders, or live-trading state.

## Implementation

- Added `scripts/export_analyst_report_quota_pack.py`.
- The exporter scans one or more report roots for valid analyst cache summaries with `stage="tushare_analyst_report_cache"` and `source="tushare_report_rc"`.
- It writes copied summaries under `quota_report_roots/` plus `analyst_report_quota_pack_manifest.json` and `.md`.
- It prints a small terminal packet with status, summary, pack root, and safety text.
- It excludes its own output directory during scans and refreshes its own `quota_report_roots/` directory on each run, making repeated exports idempotent even when the output directory is inside a scanned report root.
- Updated analyst quota preflight scanning so default broad scans such as `data\reports` skip quota-pack internals, while explicit scans of a quota-pack root still count the pack evidence.
- Added `tests/unit/test_analyst_report_quota_pack.py`.
- Added the new quota-pack test file to the laptop integration profile and profile-plan assertion.

## Test-First Evidence

- Initial pack test failed before the exporter existed.
- Laptop integration plan assertion failed before `tests/unit/test_analyst_report_quota_pack.py` was added to `scripts/run_checks.py`.
- Idempotence test failed before the exporter excluded and cleaned its own output: the second export counted `2` instead of `1`.
- Broad-scan test failed before quota-pack-aware preflight scanning: scanning the parent report root counted `2` provider windows instead of the original `1`.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `status="cleared"`, startup gate cleared `true`, blockers `0`, warnings `1`.
- CN stock data manifest: blockers `0`; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Exporter dry run against local reports:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\round518_analyst_quota_pack_20260705
```

Result:

- `status="exported"`
- `exported_report_count=8`
- `report_root_count=1`
- `skipped_report_count=0`

Explicit pack preflight:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports\round518_analyst_quota_pack_20260705 --target-date 2026-07-05 --output-dir data\reports\round518_quota_pack_preflight_20260705 --fail-on-blocked
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `target_date_matches_generated_at=true`
- `quota_scope="local_report_roots_only"`

Actual-date April cache CLI dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round518_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round518_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round518_cache_cli_quota_preflight_20260705 --quota-preflight-only
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `target_date_matches_generated_at=true`
- No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py -q
```

Combined focused verification also passed with 19 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate -q
```

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 91 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Use the quota pack as cross-machine evidence, not as a global provider-quota oracle. A safe provider-backed analyst-report cache attempt should include local reports plus every available workstation quota pack with repeated `--quota-report-root`; if any relevant pack is missing, manually confirm same-day `report_rc` usage before fetching.

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05 because the actual-date dry-run still exits `3`.
