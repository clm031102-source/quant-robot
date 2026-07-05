# Project Round546 Handoff Next Command Context

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 43 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It added explicit laptop/main-only context to the integration handoff's execution command.

## Round Objective

Round545 gave office desktop a copy-safe `handoff.here_command`. Round546 makes the companion execution command harder to misuse by adding machine-readable context and an allow/deny boolean:

- `handoff.next_command_context="laptop main only"`
- `handoff.next_command_allowed_here=false` from an office topic handoff

The allow flag is true only when the plan itself is executable with `status=="ready"`, which means the command has been rerun from the correct laptop/main integration context.

## Startup Evidence

Fresh orientation before editing:

- Local time: 2026-07-05 06:24:16 +08:00.
- Startup context: expected machine `office_desktop`, task `factor_batch`, branch matched, and upstream was `0 ahead / 0 behind`.
- Quant PM startup gate: `ready`, blockers `[]`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Topic/main relationship before edits: `0 43`; the topic branch was 43 commits ahead of `origin/main` and 0 commits behind.
- Clean-topic `--require-handoff-ready` exited `0` before this round's local edits.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added to `handoff`:

- `next_command_context`
- `next_command_allowed_here`

Expected office-topic handoff:

```json
{
  "executable_here": false,
  "here_command": "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready",
  "next_command": "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute",
  "next_command_context": "laptop main only",
  "next_command_allowed_here": false
}
```

## Test-First Evidence

Updated test first:

- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
```

Result before implementation:

- failed with `KeyError: 'next_command_context'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- focused test passed;
- full laptop integration plan unit suite passed with 7 tests.

## Decision

Office-desktop UI, docs, and operators should prefer:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

They should not execute:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

unless the current plan reports `handoff.next_command_allowed_here=true`. In normal office-topic handoff state, that flag must remain false.

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
