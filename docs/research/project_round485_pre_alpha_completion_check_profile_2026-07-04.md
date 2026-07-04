# Project Round485 Pre-Alpha Completion Check Profile

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: make the completion gate available through `scripts/run_checks.py` so any future profit-factor mining automation can stop before mining when the project is not fully integrated and observation-sufficient.

## Progress Snapshot

Estimated project completion remains 98%.

This round adds an executable pre-alpha guard. It does not clear the current project blockers:

```text
not_on_stable_branch
remote_topic_branches_remaining
observation_sufficiency_not_cleared
```

While this round is still uncommitted, the completion gate also reports:

```text
working_tree_dirty
```

That transient blocker should disappear after this documentation and code change are committed and pushed.

## Change

`scripts/run_checks.py` now supports:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha
```

The profile contains one local check step:

```text
project_completion_gate -> scripts/run_project_completion_gate.py --require-complete
```

The profile intentionally does not run factor generation, data downloads, portfolio grids, or promotion checks.

`execute_check_plan` now propagates a failed child command's exit code instead of converting it into a generic Python traceback. This lets `pre-alpha` preserve the completion gate's exit code `2` when `factor_mining_allowed=false`.

## Verification

TDD red check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_check_plan.py::CheckPlanTests::test_pre_alpha_profile_runs_completion_gate_before_factor_mining -q
```

Initial failure reason: `Unsupported check profile: pre-alpha`.

Green checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_check_plan.py -q
```

Result:

```text
9 passed
```

Profile preview:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha
```

Result: one step, `project_completion_gate`, with `uses_network=false`.

Blocked execution check:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha --execute
```

Expected result in current state:

```text
pre-alpha-exit=2
factor_mining_allowed=false
observed_fills=5
required_fills=20
fill_deficit=15
```

## Current Decision

Do not start `alpha-mine` yet.

Future automated mining should first run:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile pre-alpha --execute
```

Proceed to profit-factor mining only after this profile exits 0 and the completion gate reports:

```text
factor_mining_allowed=true
status=complete
blockers=[]
```

Laptop still owns the real completion actions: merge the remaining topic branches into `main`, verify merged `main`, push `main`, clean safe remote topic branches, then continue or re-scope paper observation until the 20-fill sufficiency gate clears.
