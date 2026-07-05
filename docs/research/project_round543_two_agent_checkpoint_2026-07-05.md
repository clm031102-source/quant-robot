# Project Round543 Two-Agent Checkpoint

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 40 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It completed the required two-agent review checkpoint.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 06:08:59 +08:00.
- Current branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Current topic head before this document: `b4226d79`.
- Git status before work: clean and synchronized with origin.
- Topic/main relationship: `0 40`.
- Startup context: branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

Integration handoff evidence:

- `--require-handoff-ready` exited `0`.
- Plan status: `blocked`.
- Blocker: `current_branch_must_be_main`.
- `handoff.status=ready_on_main`.
- `handoff.next_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`.
- Merge order commit at review time: `b4226d79d0d9e02e5ebd96f8bc2ec9d7d996c435`.

## Review Agents

Quant PM reviewer: `Aristotle`

Ordinary-user reviewer: `Hilbert`

Both were read-only reviewers. Neither edited files, ran provider/data jobs, merged, pushed, or deleted branches.

Note: Aristotle assumed `task=factor_review` and commits/pushes disallowed. Main-thread startup evidence for this round is `office_desktop / factor_batch` with commits and pushes allowed on the active topic branch. Aristotle's research go/no-go conclusions still apply because they concern provider, source, factor, LPR, and mainline boundaries.

## Quant PM Findings

Aristotle decisions:

- Research direction: go only for paper/source/process work; no-go for new alpha claims.
- Analyst-report revision remains the best orthogonal PIT source path, but April cache is blocked.
- No formula tuning, portfolio grids, promotion gates, or final-holdout reads.
- Old northbound accumulation, northbound crowding/reversal, margin-credit, and LPR/macro factors stay blocked or hibernated.
- HK-hold join and coverage evidence remains source-quality only, not IC or portfolio evidence.
- Provider/quota: no-go until required quota packs from `highspec_desktop` and `laptop` are real and complete, and actual-date preflight exits clean.
- LPR: no-go until plausible numeric cache evidence, isolated cache handling, offline repair into a fresh root, and coverage audit pass.
- Handoff/mainline: go only from laptop on `main`; office desktop should not push `main` or delete the topic branch.

Aristotle highest-value actions:

1. Run laptop-owned `project_sync` integration from laptop on `main`, rerunning the plan before execution.
2. Collect or import real quota-pack evidence from `highspec_desktop` and `laptop`; do not substitute notes for packs.
3. Complete ordinary-user safety review and update checklist/index before reconsidering provider or factor commands.

## Ordinary-User Findings

Hilbert usability verdict:

- The big rule is mostly clear: do not run provider/factor/mainline actions from `office_desktop`; real integration is laptop-owned on `main`.
- The weak spot is immediate action clarity: the most copyable command is the laptop `project_sync --execute` command, which must not be run from office desktop.

Likely mistakes:

- Copying `python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute` while still on office desktop or a topic branch.
- Reading `handoff.status=ready_on_main` as ready to run now instead of handoff-ready only after laptop is on `main`.
- Seeing startup gates clear and assuming analyst April cache, Tushare calls, LPR refresh, factor tests, or grids are allowed.
- Confusing review task labels with the current branch name.
- Treating older sections in `CURRENT_RESEARCH_INDEX.md` as current instructions instead of historical evidence.

Hilbert requested improvements:

1. Add a top Run Here / Do Not Run Here box with one current-office action and one laptop-only integration action.
2. Explain `ready_on_main` as handoff-ready, not executable here.
3. Add a plain-English blocker table.

## Run Here / Do Not Run Here

Run here on office desktop topic branch:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Meaning:

- This is an office handoff check.
- Exit `0` means the topic branch is ready to hand off.
- It does not merge `main`.
- It does not push.
- It does not delete branches.

Do not run here on office desktop:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

That command is laptop-only and must be run from `main`.

## Plain-English Blocker Table

| Area | Current Status | Blocked Because | What Unblocks It |
| --- | --- | --- | --- |
| Analyst April cache | Blocked | Required quota packs from `highspec_desktop` and `laptop` are missing; provider budget evidence remains adverse | Real required-machine packs imported and actual-date preflight exits `0` |
| Frozen analyst prescreen | Blocked | April cache has not succeeded | Run exactly once after April cache succeeds |
| LPR/macro repair | Blocked | No plausible non-missing LPR cache evidence | Explicit provider approval, plausible cache, offline repair, coverage audit pass |
| External-feed factors | Blocked | Current evidence is source-quality only; old families are hibernated | New preregistered mechanism after source gates, not old-family rerun |
| Main integration | Handoff-ready only | Current branch is not `main`; laptop owns `project_sync` | Laptop on `main` reruns plan and executes |
| Live trading | Blocked by design | Project is research-to-paper only | No unblock in this project lane |
| Generated data in Git | Blocked by policy | `data/raw`, `data/processed`, `data/reports` are forbidden | Keep generated data untracked and unstaged |

## Decisions

- No provider-consuming step is approved from office desktop.
- No factor-research action is approved before analyst quota and LPR/source blockers clear.
- Keep old source families hibernated.
- Keep `main` integration laptop-owned.
- Keep `ready_on_main` phrasing, but always pair it with the explanation: handoff-ready, not executable here.
- Round544 should use this review to harden the most copyable checklist text, not to run provider, factors, or `main` integration from office desktop.

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
