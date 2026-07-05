# Project Round538 Integration Plan Handoff Status

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 35 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It hardened the laptop integration plan output so operators do not need to chase a self-staling manual rehearsal document.

## Round Objective

Round537 recorded a latest-topic merge rehearsal, but each new documentation commit advances the topic branch by one commit. The better operator pattern is for the integration tool itself to state whether a topic-branch run is ready to hand off to laptop `main`, while still requiring a fresh rerun from `main` before execution.

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Behavior added:

- Every plan now includes a `handoff` object.
- If the plan is blocked only by `current_branch_must_be_main` and has a non-empty merge order, `handoff.status` is `ready_on_main`.
- The handoff records the required execution context:
  - `required_machine=laptop`;
  - `required_task=project_sync`;
  - `required_branch=main`;
  - `rerun_plan_before_execute=true`;
  - `merge_order_count` equal to the number of pending topic branches.
- If any other blocker is present, including a dirty worktree, `handoff.status` remains `blocked`.

This keeps the office-topic branch safe while making the laptop handoff clearer.

## Test-First Evidence

New test added first:

- `test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
```

Result before implementation:

- failed with `KeyError: 'handoff'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- focused test passed;
- full laptop integration plan unit suite passed with 6 tests.

## Local CLI Check

While the Round538 code/docs changes were still unstaged, the actual CLI correctly kept the handoff blocked:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync
```

Observed summary:

- `status=blocked`;
- blockers included `current_branch_must_be_main` and `working_tree_dirty`;
- `handoff.status=blocked`;
- merge order still pointed at the active topic branch.

Interpretation: `ready_on_main` is intentionally available only for a clean topic-branch handoff with no blockers except `current_branch_must_be_main`.

## Decision

Use the integration plan tool as the authoritative handoff surface instead of repeatedly committing fresh merge rehearsal documents after every documentation-only advance. Before laptop execution, rerun the tool from laptop on `main`; before office handoff, rerun it from the clean topic branch and require `handoff.status=ready_on_main`.

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
