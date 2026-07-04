# Project Round483 Completion Gate Require-Complete Mode

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: harden the project completion gate so automation can fail closed before profit-factor mining starts.

## Progress Snapshot

Estimated project completion remains 98%.

The gate now has an automation-safe mode:

```powershell
.\.venv\Scripts\python.exe scripts\run_project_completion_gate.py --require-complete --observation-sufficiency-pack <latest_observation_sufficiency_pack>
```

Exit behavior:

| Condition | Exit code |
| --- | ---: |
| `factor_mining_allowed=true` | 0 |
| `factor_mining_allowed=false` with `--require-complete` | 2 |
| `factor_mining_allowed=false` without `--require-complete` | 0 |

## Current Result

Current office-desktop state still blocks profit-factor mining. The `--require-complete` command returns exit code 2 because:

```text
not_on_stable_branch
remote_topic_branches_remaining
observation_sufficiency_not_cleared
```

The worktree is clean after Round482, so `working_tree_dirty` is no longer part of the blocker list.

## Usage Rule

Any future automated factor-mining entrypoint should run the require-complete gate first. If it exits nonzero, stop before generating factor candidates.

Do not start `alpha-mine` until the gate returns:

```json
{
  "status": "complete",
  "factor_mining_allowed": true,
  "blockers": []
}
```

## Decision

This keeps the 24-hour completion objective fail-closed: if laptop integration, branch cleanup, or paper-observation sufficiency is still incomplete, automation cannot accidentally begin profit-factor mining.
