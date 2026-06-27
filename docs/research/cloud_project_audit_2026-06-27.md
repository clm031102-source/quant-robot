# Cloud Project Audit

Date: 2026-06-27

Scope: GitHub branch structure, sync safety, cloud entry documentation, workstation ownership, and research-to-paper repository hygiene.

## Executive Summary

The cloud repository is structurally clean after the branch consolidation:

- `origin/main` is the only durable remote branch.
- There are no remote `origin/codex/*` topic branches.
- The CN stock sprint branch, CN ETF batch branch, and temporary ETF integration branch were integrated into `main` and deleted from GitHub.
- `sync_project.py --machine laptop --task project_sync` reports no pending research branches, no pending topic branches, no cleanup branches, no blocked paths, and no branch-discovery errors.

The main issue found during this audit was documentation drift: `docs/research/CURRENT_RESEARCH_INDEX.md` still described deleted branches as active or pending. This was fixed and guarded by a unit test.

## Evidence

Fresh audit commands used during cleanup:

```powershell
git branch -r --format='%(refname:short)|%(objectname:short)'
python scripts\sync_project.py --machine laptop --task project_sync
python scripts\run_project_audit.py --json
python -m unittest -v tests.unit.test_start_task_context tests.unit.test_sync_project
```

Observed remote branch inventory after cleanup:

```text
origin|c02d0736
origin/main|c02d0736
```

## Findings And Fixes

| Finding | Severity | Fix |
| --- | --- | --- |
| Cloud index still listed deleted branches as active/pending | High | Rewrote `docs/research/CURRENT_RESEARCH_INDEX.md` to state that remote topic branches are `none` and cleanup is complete |
| README did not state the post-cleanup remote structure | Medium | Added a current-status note that `origin/main` is the only durable remote branch |
| No direct regression test protected the cloud index from stale branch wording | Medium | Added `tests/unit/test_cloud_project_docs.py` |
| `factor_integration` had no valid owner before the previous cleanup | Fixed earlier in same cleanup sequence | `configs/workstations.json` assigns `factor_integration` to `laptop` only |

## Current Operating Model

- `main` is the only stable cloud branch.
- Laptop owns architecture, integration, mainline merge decisions, and cloud cleanup.
- High-spec desktop and office desktop own heavy data generation, factor batches, validation reruns, and data-quality checks.
- Desktop machines should not merge research branches to `main`.
- Generated data and reports remain local-only under `data/`.

## Remaining Risks

- The project has many historical research docs. They are useful evidence, but the first-read index must stay current or users will follow stale branch instructions.
- A local-only branch named `codex/factor-batch-moneyflow-alpha` may still exist on this machine. It is not a cloud branch and should not be pushed unless a new review plan says why.
- Full `unittest discover` can be slow or hang on data-heavy tests. Use targeted cloud/sync/ETF tests for branch cleanup, and reserve full checks for longer validation windows.

## Required Future Guardrail

Every cloud cleanup or branch merge must end with:

```powershell
python scripts\sync_project.py --machine laptop --task project_sync
python -m unittest -v tests.unit.test_cloud_project_docs tests.unit.test_sync_project tests.unit.test_start_task_context
```

Do not claim the cloud is clean unless both the Git branch inventory and the project sync audit agree.
