# Project Round539 Integration Handoff Ready Gate

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 36 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It added a machine-checkable handoff-ready gate to the laptop integration plan CLI.

## Round Objective

Round538 added `handoff.status=ready_on_main` for a clean topic-branch handoff. Round539 makes that signal usable in scripts by adding an exit-code gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

## Change

Updated:

- `scripts/run_laptop_topic_integration_plan.py`
- `tests/unit/test_laptop_topic_integration_plan.py`

Implemented:

- New helper: `plan_handoff_ready(plan)`.
- New CLI flag: `--require-handoff-ready`.
- Exit behavior:
  - exits `0` when the plan is ready on `main`;
  - exits `0` when `handoff.status=ready_on_main` from a clean topic-branch handoff;
  - exits `2` when handoff is not ready, including dirty worktree or other blockers.

This is separate from `--require-ready`, which remains stricter and still requires true executable `status=ready`.

## Test-First Evidence

New test added first:

- `test_plan_handoff_ready_accepts_ready_on_main_or_ready_plan_only`

Observed red evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_handoff_ready_accepts_ready_on_main_or_ready_plan_only
```

Result before implementation:

- failed with `ImportError: cannot import name 'plan_handoff_ready'`.

Green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan.LaptopTopicIntegrationPlanTests.test_plan_handoff_ready_accepts_ready_on_main_or_ready_plan_only
.\.venv\Scripts\python.exe -m unittest tests.unit.test_laptop_topic_integration_plan
```

Results after implementation:

- focused test passed;
- full laptop integration plan unit suite passed with 7 tests.

## CLI Evidence

Help includes the new flag:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --help
```

Dirty-worktree gate check during Round539 development:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Result:

- exited `2`, because the current branch had unstaged Round539 changes.

Interpretation: the handoff-ready gate refuses a dirty topic branch, as intended.

## Decision

Use `--require-handoff-ready` for office-topic handoff checks after code/docs are committed. Use `--require-ready` or `--execute` only from laptop on `main`.

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
