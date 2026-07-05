# Round522 Quota Preflight Pack Provenance

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round522 lifted quota-pack provenance into the preflight evidence itself. Round521 made each pack manifest self-describing, but reviewers still had to open pack manifests separately after reading a quota preflight packet. This round makes the preflight packet, Markdown report, standalone CLI output, and cache CLI output show the provenance of explicitly scanned quota packs.

## Implementation

- `src/quant_robot/ops/analyst_report_quota_preflight.py` now detects explicit `--report-root` values that are quota-pack roots.
- The preflight packet records top-level `quota_pack_provenance`.
- `summary.quota_pack_root_count` records the number of explicit pack roots found.
- Each pack provenance row records:
  - `quota_pack_root`
  - `machine`
  - `task`
  - `branch`
  - `generated_at`
  - `exported_report_count`
- The Markdown preflight report now includes a `Quota Pack Provenance` table.
- `scripts/run_analyst_report_quota_preflight.py` prints `quota_pack_provenance` in terminal JSON.
- `scripts/run_tushare_analyst_report_cache.py` prints the same provenance during its quota-preflight step.

Broad scans such as `data\reports` still do not recursively treat old quota packs as implicit external roots. Provenance is summarized for explicit pack roots.

## Test-First Evidence

The new test was written before implementation:

- `test_preflight_summarizes_explicit_quota_pack_provenance` exported a provenance-aware quota pack, then ran standalone preflight against that pack root.
- The test expected `summary.quota_pack_root_count=1`, top-level `quota_pack_provenance`, Markdown provenance output, and CLI stdout provenance.
- The test failed first with `KeyError: 'quota_pack_root_count'`.
- After implementation, the specific red test, the full quota-pack suite, and the quota-preflight suite passed.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `status="cleared"`, startup gate cleared `true`, blockers `0`, warnings `1`.
- CN stock data manifest: blockers `0`; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Standalone preflight with local reports plus the Round521 provenance-aware pack:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --target-date 2026-07-05 --output-dir data\reports\round522_quota_pack_provenance_preflight_20260705 --fail-on-blocked
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `quota_pack_root_count=1`
- provenance machine: `office_desktop`
- provenance task: `factor_batch`
- provenance branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Cache CLI dry-run with the same roots:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round522_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round522_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round522_cache_cli_quota_preflight_20260705 --quota-preflight-only
```

Result:

- Exit code: `3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `quota_pack_root_count=1`
- terminal JSON included the same pack provenance
- No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py -q
```

Combined focused verification also passed with 24 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_pack.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate -q
```

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 96 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Quota preflight evidence now shows which explicit cross-machine packs were included, where they came from, and how many reports they exported. Future preflight review should read `quota_pack_provenance` together with `report_roots`, `duplicate_evidence_rows`, and `duplicate_window_rows`.

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05 because the actual-date cache CLI dry-run still exits `3`.
