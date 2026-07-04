# Project Round541 Integration Handoff Next Command

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 38 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It made the integration handoff output easier for an operator to follow.

## Round Objective

Round540 proved the clean topic branch can pass `--require-handoff-ready`, but the JSON handoff still did not include the exact next command for laptop execution. Round541 adds that command to the handoff object so an operator can inspect one machine-readable packet and see both the required context and next action.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added:

- `handoff.next_command`

Value:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

This is guidance for laptop on `main`; it is not permission to execute from office desktop.

## Test-First Evidence

Updated test first:

- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
```

Result before implementation:

- failed with `KeyError: 'next_command'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- focused test passed;
- full laptop integration plan unit suite passed with 7 tests.

## Local CLI Check

During Round541 development, the actual CLI emitted `handoff.next_command` while keeping `handoff.status=blocked` because the worktree was dirty. That preserves the Round539 safety rule: guidance can be visible before commit, but handoff readiness still requires a clean branch.

## Decision

Future office-topic handoff checks should inspect:

- `handoff.status`;
- `handoff.required_machine`;
- `handoff.required_task`;
- `handoff.required_branch`;
- `handoff.next_command`.

Only laptop on `main` should run the next command.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run external-feed portfolio grids or promotion gates from coverage audit, join smoke, or repair reports.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
