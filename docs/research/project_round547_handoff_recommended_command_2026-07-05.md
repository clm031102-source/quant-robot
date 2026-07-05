# Project Round547 Handoff Recommended Command

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 44 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It added a single recommended handoff command field so callers do not need to infer which command is safe for the current context.

## Round Objective

Round546 made `handoff.next_command` explicitly laptop/main-only. Round547 adds `handoff.recommended_command` and `handoff.recommended_command_action`:

- true executable laptop/main plans recommend `handoff.next_command` with action `execute_integration`;
- clean office-topic handoffs recommend `handoff.here_command` with action `check_handoff_ready`;
- ordinary blocked plans recommend no command and action `resolve_blockers`.

This keeps copyable command selection machine-readable and fail-closed.

## Startup Evidence

Fresh orientation before editing:

- Local time: 2026-07-05 06:31:07 +08:00.
- Startup context: expected machine `office_desktop`, task `factor_batch`, branch matched, and upstream was `0 ahead / 0 behind`.
- Quant PM startup gate: `ready`, blockers `[]`.
- CN stock factor-mining startup gate: blocked without the full confirmation set; this was not treated as provider or factor clearance.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Topic/main relationship before edits: `0 44`; the topic branch was 44 commits ahead of `origin/main` and 0 commits behind.
- Clean-topic `--require-handoff-ready` exited `0` before this round's local edits.
- Handoff status before edits: `ready_on_main`, `executable_here=false`, and merge order pointed at `d8cc2e898939e871fd7628d74a1ca5e94636b72c`.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added to `handoff`:

- `recommended_command`
- `recommended_command_action`

Expected clean office-topic handoff:

```json
{
  "status": "ready_on_main",
  "executable_here": false,
  "recommended_command": "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready",
  "recommended_command_action": "check_handoff_ready",
  "next_command": "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute",
  "next_command_allowed_here": false
}
```

Expected true laptop/main ready plan:

```json
{
  "status": "ready",
  "executable_here": true,
  "recommended_command": "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute",
  "recommended_command_action": "execute_integration",
  "next_command_allowed_here": true
}
```

Expected ordinary blocked plan:

```json
{
  "recommended_command": null,
  "recommended_command_action": "resolve_blockers"
}
```

## Test-First Evidence

Updated tests first:

- `test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands`
- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`
- `test_plan_blocks_when_not_laptop_main_project_sync_or_clean`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_blocks_when_not_laptop_main_project_sync_or_clean
```

Results before implementation:

- ready plan failed with `KeyError: 'recommended_command'`;
- clean topic handoff failed with `KeyError: 'recommended_command'`;
- ordinary blocked plan failed because it returned the handoff-check command instead of `None`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_blocks_when_not_laptop_main_project_sync_or_clean
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- three focused tests passed;
- full laptop integration plan unit suite passed with 7 tests.

## Decision

Consumers should display `handoff.recommended_command` as the first copyable command only when it is non-null. If it is null, show `handoff.recommended_command_action=resolve_blockers` and the blocker list first.

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
