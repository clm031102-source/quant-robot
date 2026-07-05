# Round519 Quota Pack Deduplication

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round519 hardened the Round518 cross-machine analyst-report quota pack workflow. Round518 made quota evidence portable, but follow-up testing found two operational edge cases:

- The same local report exported into two pack directories could be counted twice when both packs were passed to quota preflight.
- A broad exporter scan of `data\reports` could re-export old quota-pack internals, inflating a new pack.

This round keeps quota packs useful for cross-machine evidence while preventing copied evidence from masquerading as additional provider requests.

## Implementation

- `scripts/export_analyst_report_quota_pack.py` now writes `quota_pack_source_fingerprint` into each exported cache-summary JSON.
- The source fingerprint is stable for a given original cache report path and payload.
- Exported manifests now record each report's `source_fingerprint`.
- Exporter broad scans skip internals of any directory containing `analyst_report_quota_pack_manifest.json`.
- `src/quant_robot/ops/analyst_report_quota_preflight.py` now builds a row-level quota evidence fingerprint.
- Preflight deduplicates rows that share the same source fingerprint, generated date, window, status, and rate-limit fields.
- Preflight summary now records `duplicate_evidence_rows`.
- The Markdown preflight report includes the number of duplicate evidence rows skipped.

Ordinary local reports remain distinct because their source fingerprint includes their resolved source path. Two real cache reports from different paths still count separately.

## Test-First Evidence

The new tests were written before implementation and failed for the intended reasons:

- `test_duplicate_exported_pack_evidence_counts_once`: failed with `2 != 1` because two packs exported from the same source counted as two provider windows.
- `test_local_report_and_its_exported_pack_count_once`: failed with `2 != 1` because a local report plus its own pack counted twice.
- `test_export_broad_scan_skips_existing_quota_pack_internals`: failed with `2 != 1` because a fresh broad export re-exported an existing pack's internal copy.

Focused verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py -q
```

Result: 5 quota-pack tests passed and 16 quota-preflight tests passed.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `status="cleared"`, startup gate cleared `true`, blockers `0`, warnings `1`.
- CN stock data manifest: blockers `0`; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Corrected exporter run:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\round519_analyst_quota_pack_dedup_20260705
```

Result:

- `status="exported"`
- `exported_report_count=8`
- `report_root_count=1`
- `skipped_report_count=0`

Actual-date April cache CLI dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round519_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round519_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round519_cache_cli_quota_preflight_20260705 --quota-preflight-only
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

Explicit dedup preflight with local reports plus repeated Round519 pack:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --report-root data\reports\round519_analyst_quota_pack_dedup_20260705 --report-root data\reports\round519_analyst_quota_pack_dedup_20260705 --target-date 2026-07-05 --output-dir data\reports\round519_quota_pack_dedup_preflight_20260705 --fail-on-blocked
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `report_root_count=3`

## Verification

Combined focused verification passed with 22 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate -q
```

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 94 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Quota packs are now safer to pass around and repeat in commands. Repeated copies of the same exported cache-summary evidence no longer inflate same-day provider request counts, and fresh broad exports no longer recursively absorb old quota packs.

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05 because the actual-date cache CLI dry-run still exits `3`.
