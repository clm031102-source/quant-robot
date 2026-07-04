# Project Round545 Handoff Here Command

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 42 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It further separated safe office-topic commands from laptop-only execution commands in the integration handoff JSON.

## Round Objective

Round544 made `ready_on_main` non-executable in the current office context by adding `handoff.executable_here=false`. Round545 adds a separate `handoff.here_command` so the most copyable command for office desktop is the safe handoff check, not the laptop-only execute command.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Added to `handoff`:

- `here_command`

Value:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Existing `handoff.next_command` remains laptop-only:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

## Test-First Evidence

Updated test first:

- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
```

Result before implementation:

- failed with `KeyError: 'here_command'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- focused test passed;
- full laptop integration plan unit suite passed with 7 tests.

## Decision

For office desktop handoff instructions, display or copy `handoff.here_command` first. Treat `handoff.next_command` as laptop-only and only usable from laptop on `main`.

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
