# Project Round551 Handoff Context Mismatch Reasons

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 48 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It added explicit current-context mismatch reasons to the handoff object.

## Round Objective

Round550 exposed the current planning context inside `handoff`. Round551 adds:

- `handoff.current_context_mismatch_reasons`

This lets handoff-only consumers explain why `current_context_matches_required=false` without re-deriving the reason from `current_machine`, `current_task`, and `current_branch`.

## Startup Evidence

Fresh orientation before editing:

- Local time: 2026-07-05 06:52:42 +08:00.
- Startup context: expected machine `office_desktop`, task `factor_batch`, branch matched, and upstream was `0 ahead / 0 behind`.
- Quant PM startup gate: `ready`, blockers `[]`.
- CN stock factor-mining startup gate: blocked without the full confirmation set; this was not treated as provider or factor clearance.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Topic/main relationship before edits: `0 48`; the topic branch was 48 commits ahead of `origin/main` and 0 commits behind.
- Clean-topic `--require-handoff-ready` exited `0` before this round's local edits.
- Clean-topic handoff before edits: `ready_on_main`, `ready_for_handoff=true`, `current_context_matches_required=false`, `recommended_command_action=check_handoff_ready`, and merge order pointed at `9c67c9eafe64abeae2b34a34b997e16a593d6f8d`.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added to `handoff`:

- `current_context_mismatch_reasons`

Expected true executable laptop/main plan:

```json
{
  "current_context_matches_required": true,
  "current_context_mismatch_reasons": []
}
```

Expected clean topic handoff:

```json
{
  "current_context_matches_required": false,
  "current_context_mismatch_reasons": ["current_branch_must_be_main"],
  "ready_for_handoff": true,
  "recommended_command_action": "check_handoff_ready"
}
```

Expected wrong machine/task/topic context:

```json
{
  "current_context_matches_required": false,
  "current_context_mismatch_reasons": [
    "machine_must_be_laptop",
    "task_must_be_project_sync",
    "current_branch_must_be_main"
  ],
  "recommended_command_action": "resolve_blockers"
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

- all three focused tests failed with `KeyError: 'current_context_mismatch_reasons'`.

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

Handoff consumers should display `handoff.current_context_mismatch_reasons` when `handoff.current_context_matches_required=false`. A branch-only mismatch may still be handoff-ready from a clean topic branch, but it is not executable here.

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
