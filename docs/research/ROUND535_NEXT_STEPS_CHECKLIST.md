# Round535 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 32 after the Round504 review-agent baseline.
- Latest cloud/main audit: Round535.
- Remote default: `origin/HEAD -> origin/main`.
- Stable branch: `origin/main` at `af474d5a`.
- Active topic branch: `origin/codex/factor-batch-cn-stock-profit-mining-20260704` at `8b101170`.
- Remote topic branches after prune: exactly one active branch.
- `origin/main` is an ancestor of the active topic branch.
- Topic branch is 32 commits ahead of `origin/main` and 0 commits behind.
- No stale merged remote topic branches were present.
- No safe-sync cleanup action was recommended.

## Cloud Branch Rule

Keep both current remote branches:

- keep `origin/main` as stable branch;
- keep `origin/codex/factor-batch-cn-stock-profit-mining-20260704` as active research branch.

Do not merge to `main` or delete the active branch during routine `factor_batch` continuation. Treat either action as a separate project-sync or branch-integration task with explicit intent.

## Required Startup Block

```powershell
$MACHINE = "office_desktop"
$TASK = "factor_batch"
$BRANCH = "codex/factor-batch-cn-stock-profit-mining-20260704"

git fetch --prune
git status --short --branch
git branch -r --format="%(refname:short) %(objectname:short)"
git rev-list --left-right --count origin/main...origin/codex/factor-batch-cn-stock-profit-mining-20260704

.\.venv\Scripts\python.exe scripts\start_task_context.py --machine $MACHINE --task $TASK --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine $MACHINE --task $TASK --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine $MACHINE --task $TASK --branch $BRANCH --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if the current branch is not synchronized, if remote branches changed unexpectedly, or if any startup gate reports blockers.

## Integration Preconditions

Before any future merge to `main`, require:

- explicit user intent to integrate the active branch into `main`;
- clean working tree;
- `git fetch --prune`;
- branch relationship audit;
- full validation profile selected for the integration task;
- safe-sync audit with `branch_discovery.errors=[]`;
- confirmation that generated `data/` outputs are untracked and unstaged;
- decision on whether to keep, archive, or delete the topic branch after merge.

## Cleanup Preconditions

Before deleting any remote topic branch, require one of:

- the branch is merged to `origin/main`;
- the branch is marked absorbed by the project manifest;
- the branch is explicitly ignored by the project manifest.

Never delete:

- `origin/main`;
- the active research branch while it is still the current working branch;
- any branch that is not an ancestor of `origin/main` unless an explicit manifest rule says it is absorbed or ignored.

## Research Work Boundary

Still blocked:

- analyst April cache execution;
- frozen January-April prescreen;
- LPR provider refresh without explicit provider approval;
- external-feed factor revival;
- portfolio grids;
- promotion gates;
- final-holdout reads.

Allowed if prerequisites change:

- import missing quota packs from `highspec_desktop` and `laptop`;
- run one actual-date analyst quota preflight after quota date or pack evidence changes;
- run isolated LPR cache refresh only after explicit provider approval.

## Round543 Reminder

Round543 is the next required two-agent checkpoint. If cloud/main structure remains stable and provider blockers still hold, use Round543 for another Quant PM plus ordinary-user review before any source-family or factor decision.
