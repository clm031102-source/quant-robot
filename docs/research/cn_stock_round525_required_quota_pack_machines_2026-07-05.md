# Round525 Required Quota Pack Machines

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round525 converted the Round524 cross-machine quota checklist into a machine-checkable preflight constraint. Instead of relying only on a manual table saying `highspec_desktop` and `laptop` are unknown, quota preflight can now be told which quota-pack source machines are required and can block provider-backed cache attempts when any required machine is missing.

No provider-backed Tushare cache was run.

## Implementation

- `src/quant_robot/ops/analyst_report_quota_preflight.py` accepts `required_quota_pack_machines`.
- The preflight summary now records:
  - `required_quota_pack_machines`
  - `present_quota_pack_machines`
  - `missing_required_quota_pack_machines`
- Missing required machines add the blocker `missing_required_quota_pack_machines`.
- When this blocker is present, `decision.next_action` becomes `collect_required_quota_pack_evidence`.
- The Markdown preflight report includes a `Required Quota Pack Machines` section.
- `scripts/run_analyst_report_quota_preflight.py` exposes repeated `--required-quota-pack-machine`.
- `scripts/run_tushare_analyst_report_cache.py` exposes repeated `--quota-required-pack-machine` and passes the requirement into the default quota preflight.

Existing behavior is unchanged when no required machines are specified.

## Test-First Evidence

The new tests were written before implementation:

- `test_preflight_blocks_when_required_quota_pack_machine_is_missing`
- `test_cache_cli_blocks_when_required_quota_pack_machine_is_missing`
- existing help tests were extended to require the new CLI options.

The focused test run failed first because the new CLI options were missing and no preflight evidence packet was written. After implementation, the focused quota-preflight and quota-pack suites passed with 27 tests.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: run with `--commits-allowed --pushes-allowed --confirm-start`; `status="cleared"` and blockers `[]`.
- CN stock data manifest: `status="review_required"`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Required-Machine Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round525_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round525_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round525_required_machine_quota_preflight_20260705 --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-preflight-only
```

Result:

- `LASTEXITCODE=3`
- `status="blocked"`
- blockers: `daily_provider_request_budget_exhausted`, `missing_required_quota_pack_machines`
- `next_action="collect_required_quota_pack_evidence"`
- `target_date_matches_generated_at=true`
- `quota_scope="local_report_roots_only"`
- `required_quota_pack_machines`: `office_desktop`, `highspec_desktop`, `laptop`
- `present_quota_pack_machines`: `office_desktop`
- `missing_required_quota_pack_machines`: `highspec_desktop`, `laptop`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `remaining_request_windows=0`

No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py -q
```

Result: 27 tests passed.

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 100 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Future April 2024 cache attempts should include all required workstation machine constraints:

```powershell
--quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop
```

Do not run provider-backed April cache until the actual-date preflight exits `0`, `missing_required_quota_pack_machines=[]`, and all provider-cache criteria from the next checklist are satisfied.
