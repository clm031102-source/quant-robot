# Round543 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 40 after the Round504 review-agent baseline.
- Latest required two-agent checkpoint: Round543 completed.
- Quant PM reviewer: `Aristotle`.
- Ordinary-user reviewer: `Hilbert`.
- Next required two-agent checkpoint: Round553.
- Handoff status: `ready_on_main`, meaning handoff-ready and not executable here.

## Run Here

Office desktop topic branch handoff check:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

Use this only to confirm the topic branch is ready to hand off.

## Do Not Run Here

Do not run this on office desktop or on the topic branch:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

That command is for laptop on `main`.

## Next Best Actions

Preferred:

- laptop runs project-sync integration from `main`;
- import real quota packs from `highspec_desktop` and `laptop`;
- improve checklist wording where `ready_on_main` might look executable.

Allowed on office desktop before blockers clear:

- non-provider docs;
- tests;
- source-tooling guardrails;
- handoff clarity improvements.

## Blocker Table

| Area | Status | Do Next |
| --- | --- | --- |
| Analyst April cache | Blocked | Import real quota packs and rerun actual-date preflight only when allowed |
| Frozen analyst prescreen | Blocked | Run exactly once only after April cache succeeds |
| LPR refresh | Blocked | Requires explicit provider approval |
| LPR repair/factors | Blocked | Requires plausible cache, offline repair, and coverage audit |
| Old external families | Hibernated | Do not reopen without a new preregistered mechanism |
| Main integration | Laptop-only | Run from laptop on `main`, not office topic branch |
| Live trading | Out of scope | Keep research-to-paper only |

## Still Forbidden

- Tushare provider calls without cleared gates.
- Analyst April cache now.
- Frozen analyst prescreen now.
- LPR provider refresh now.
- External-feed factor tests.
- Portfolio grids.
- Promotion gates.
- Final-holdout reads.
- Office-desktop `main` push.
- Remote branch deletion from office desktop.
- Staging generated `data/` outputs.
