# Round520 Quota Duplicate Evidence Details

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round520 made the Round519 quota-pack deduplication auditable. Round519 correctly skipped repeated pack evidence, but the durable preflight packet only recorded a count. That was enough for enforcement, but weak for cross-machine review because a reviewer could not inspect which rows were skipped or which report path was kept.

This round adds duplicate-row details to the analyst-report quota preflight packet and Markdown report.

## Implementation

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now records `duplicate_window_rows` at the packet top level.
- Each duplicate detail records:
  - `quota_evidence_fingerprint`
  - `kept_report_path`
  - `duplicate_report_path`
  - `generated_at`
  - `window_start`
  - `window_end`
  - `status`
  - `counts_against_quota`
  - `provider_rate_limit`
  - `retry_after_seconds`
- The Markdown report now includes a `Duplicate Evidence Rows` section before blockers.
- The existing `duplicate_evidence_rows` summary count remains unchanged.

## Test-First Evidence

The new assertion was added before implementation:

- `test_duplicate_exported_pack_evidence_counts_once` expected `duplicate_window_rows` to contain one detail row with kept/duplicate report paths, the `20240401..20240430` window, and a nonempty evidence fingerprint.
- The test failed first with `KeyError: 'duplicate_window_rows'`.
- After implementation, focused quota-pack and quota-preflight tests passed.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `status="cleared"`, startup gate cleared `true`, blockers `0`, warnings `1`.
- CN stock data manifest: blockers `0`; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Explicit preflight with local reports plus the same Round519 pack twice:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --report-root data\reports\round519_analyst_quota_pack_dedup_20260705 --report-root data\reports\round519_analyst_quota_pack_dedup_20260705 --target-date 2026-07-05 --output-dir data\reports\round520_quota_pack_duplicate_detail_preflight_20260705 --fail-on-blocked
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `duplicate_window_rows` detail count: 2
- First duplicate detail had kept and duplicate report paths and window `20240201..20240229`

Actual-date April cache CLI dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round520_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round520_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round520_cache_cli_quota_preflight_20260705 --quota-preflight-only
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=0`
- `target_date_matches_generated_at=true`
- No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py -q
```

Combined focused verification also passed with 22 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate -q
```

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 94 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Quota-pack deduplication is now auditable, not just enforced. Future cross-machine preflight packets can show which duplicate evidence was skipped and which report path supplied the counted row.

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05 because the actual-date cache CLI dry-run still exits `3`.
