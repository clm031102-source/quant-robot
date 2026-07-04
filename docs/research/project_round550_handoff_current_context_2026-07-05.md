# Project Round550 Handoff Current Context

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 47 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It made the handoff object include the current execution context as well as the required context.

## Round Objective

Round549 exposed `handoff.ready_for_handoff`. Round550 adds:

- `handoff.current_machine`
- `handoff.current_task`
- `handoff.current_branch`
- `handoff.current_context_matches_required`

This lets tools that read only `handoff` compare current context against the required laptop/main project-sync context without reading top-level `selected` and `git` fields.

## Startup Evidence

Fresh orientation before editing:

- Local time: 2026-07-05 06:47:23 +08:00.
- Startup context: expected machine `office_desktop`, task `factor_batch`, branch matched, and upstream was `0 ahead / 0 behind`.
- Quant PM startup gate: `ready`, blockers `[]`.
- CN stock factor-mining startup gate: blocked without the full confirmation set; this was not treated as provider or factor clearance.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Topic/main relationship before edits: `0 47`; the topic branch was 47 commits ahead of `origin/main` and 0 commits behind.
- Clean-topic `--require-handoff-ready` exited `0` before this round's local edits.
- Clean-topic handoff before edits: `ready_on_main`, `ready_for_handoff=true`, `executable_here=false`, `recommended_command_action=check_handoff_ready`, and merge order pointed at `3e1463b954d522f9c6eab7fa679a93dca2e2d09e`.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added to `handoff`:

- `current_machine`
- `current_task`
- `current_branch`
- `current_context_matches_required`

Expected clean office-topic handoff when planned with `--machine laptop --task project_sync`:

```json
{
  "status": "ready_on_main",
  "current_machine": "laptop",
  "current_task": "project_sync",
  "current_branch": "codex/factor-batch-cn-stock-profit-mining-20260704",
  "current_context_matches_required": false,
  "required_machine": "laptop",
  "required_task": "project_sync",
  "required_branch": "main"
}
```

Expected true executable laptop/main plan:

```json
{
  "status": "ready",
  "current_machine": "laptop",
  "current_task": "project_sync",
  "current_branch": "main",
  "current_context_matches_required": true,
  "executable_here": true
}
```

## Test-First Evidence

Updated tests first:

- `test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands`
- `test_plan_blocks_when_not_laptop_main_project_sync_or_clean`
- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_blocks_when_not_laptop_main_project_sync_or_clean
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
```

Results before implementation:

- all three focused tests failed with `KeyError: 'current_machine'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_blocks_when_not_laptop_main_project_sync_or_clean
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- three focused tests passed;
- full laptop integration plan unit suite passed with 8 tests.

## Decision

Handoff consumers should compare `handoff.current_*` with `handoff.required_*` before displaying an execute action. `current_context_matches_required=false` can still be a valid handoff state when `ready_for_handoff=true`; it means the current context may run the handoff check, not the laptop/main execute command.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No Tushare provider call.
- No analyst cache or prescreen run.
- No LPR provider refresh or repaired processed-data write.
- No external-feed factor test, portfolio grid, promotion gate, or final-holdout read.
- No office-desktop `main` push.
- No remote branch deletion from office desktop.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
