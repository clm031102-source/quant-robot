# Round526 Quota Machine Notes

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round526 added audit-only notes for missing quota-pack machines. Round525 made required quota-pack source machines machine-checkable, but the next checklist also asked for an unavailable reason and confirmation timestamp when a pack cannot be produced. This round records that context in the preflight packet without treating it as quota evidence.

No provider-backed Tushare cache was run.

## Implementation

- `src/quant_robot/ops/analyst_report_quota_preflight.py` accepts `quota_pack_machine_notes`.
- The preflight summary records `quota_pack_machine_notes` as machine/note rows.
- The Markdown report includes a `Quota Pack Machine Notes` section.
- The Markdown explicitly states that note context is audit-only and does not satisfy required pack evidence.
- `scripts/run_analyst_report_quota_preflight.py` exposes repeated `--quota-pack-machine-note MACHINE=NOTE`.
- `scripts/run_tushare_analyst_report_cache.py` exposes the same repeated option and passes notes into quota preflight.

Missing required machines still add `missing_required_quota_pack_machines` and still block provider-backed cache.

## Test-First Evidence

The new tests were written before implementation:

- `test_required_machine_notes_are_audited_but_do_not_satisfy_missing_pack`
- existing CLI help tests were extended to require `--quota-pack-machine-note`
- the cache CLI missing-machine test was extended to pass a note and assert it appears in stdout and JSON

The focused test run failed first because `quota_pack_machine_notes` and the new CLI option did not exist. After implementation, the focused quota-preflight and quota-pack suites passed with 28 tests.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: run with `--commits-allowed --pushes-allowed --confirm-start`; `status="cleared"` and blockers `[]`.
- CN stock data manifest: `status="review_required"`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Note-Aware Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round526_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round526_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round526_machine_note_quota_preflight_20260705 --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=pack unavailable on office desktop at 2026-07-05 04:17 +08:00" --quota-pack-machine-note "laptop=pack unavailable on office desktop at 2026-07-05 04:17 +08:00" --quota-preflight-only
```

Result:

- `LASTEXITCODE=3`
- `status="blocked"`
- blockers: `daily_provider_request_budget_exhausted`, `missing_required_quota_pack_machines`
- `next_action="collect_required_quota_pack_evidence"`
- `target_date_matches_generated_at=true`
- `required_quota_pack_machines`: `office_desktop`, `highspec_desktop`, `laptop`
- `present_quota_pack_machines`: `office_desktop`
- `missing_required_quota_pack_machines`: `highspec_desktop`, `laptop`
- `quota_pack_machine_notes` recorded both missing machines and the office-desktop confirmation note
- `remaining_request_windows=0`

No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py -q
```

Result: 28 tests passed.

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 101 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Future preflight reviews can record missing-machine context with `--quota-pack-machine-note`, but these notes do not satisfy required pack evidence. Provider-backed April cache remains blocked until:

- actual-date preflight exits `0`;
- `missing_required_quota_pack_machines=[]`;
- `remaining_request_windows >= 1`;
- all provider-cache criteria from the next checklist are satisfied.
