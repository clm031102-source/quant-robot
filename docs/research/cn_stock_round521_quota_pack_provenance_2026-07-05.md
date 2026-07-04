# Round521 Quota Pack Provenance

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round521 made cross-machine analyst-report quota packs easier to review after they are shared out of band. Rounds 518-520 made quota packs portable, deduplicated, and auditable, but the pack manifest did not say which workstation, task, or branch produced the pack. That made provenance depend on directory naming conventions.

This round adds explicit pack provenance to the exporter output.

## Implementation

- `scripts/export_analyst_report_quota_pack.py` now accepts:
  - `--machine`
  - `--task`
  - `--branch`
- The pack manifest now includes:

```json
"provenance": {
  "machine": "...",
  "task": "...",
  "branch": "..."
}
```

- The Markdown manifest prints machine, task, and branch.
- The terminal JSON includes the same `provenance` object.
- Existing calls without these options still work and write empty provenance fields.

## Test-First Evidence

The new test was written before implementation:

- `test_exports_pack_provenance_for_cross_machine_review` called the exporter with `--machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704`.
- The test failed first with `unrecognized arguments: --machine ... --task ... --branch ...`.
- After implementation, the pack test suite passed.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `status="cleared"`, startup gate cleared `true`, blockers `0`, warnings `1`.
- CN stock data manifest: blockers `0`; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Provenance-aware exporter run:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\round521_analyst_quota_pack_provenance_20260705 --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
```

Result:

- `status="exported"`
- `exported_report_count=8`
- `report_root_count=1`
- `skipped_report_count=0`
- provenance machine: `office_desktop`
- provenance task: `factor_batch`
- provenance branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Actual-date April cache CLI dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round521_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round521_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round521_cache_cli_quota_preflight_20260705 --quota-preflight-only
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

Combined focused verification also passed with 23 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate -q
```

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 95 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Quota packs now carry explicit source context. Future cross-machine pack exports should pass `--machine`, `--task`, and `--branch` so reviewers can identify the origin without relying on folder names.

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05 because the actual-date cache CLI dry-run still exits `3`.
