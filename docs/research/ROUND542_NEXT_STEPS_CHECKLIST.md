# Round542 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 39 after the Round504 review-agent baseline.
- Next required two-agent checkpoint: Round543.
- Latest briefing for reviewers: Round542.
- Active topic branch at briefing time: `253e48d7`.
- Topic branch was 39 commits ahead of `origin/main` and 0 behind.
- Startup gates were clear.
- CN stock data manifest had no blockers and retained the known warnings.
- No generated `data/` paths were tracked.
- Laptop integration handoff status: `ready_on_main`.

## Round543 Required Reviewers

Create two fresh reviewers:

- Quant PM reviewer: assess research direction, source-family blocks, provider/quota/LPR decisions, and mainline handoff quality.
- Ordinary-user reviewer: assess whether a non-expert can safely understand the next command, machine context, provider risk, and stop conditions.

## Default Before Review

Do not run:

- Tushare provider calls;
- analyst April cache;
- frozen analyst prescreen;
- LPR provider refresh;
- external-feed factor tests;
- portfolio grids;
- promotion gates;
- final-holdout reads;
- office-desktop `main` push;
- remote branch deletion.

## Evidence To Show Reviewers

Use:

- `docs/research/project_round542_pre_agent_checkpoint_briefing_2026-07-05.md`;
- `docs/research/ROUND542_NEXT_STEPS_CHECKLIST.md`;
- `docs/research/project_round540_clean_handoff_ready_verification_2026-07-05.md`;
- `docs/research/project_round539_integration_handoff_ready_gate_2026-07-05.md`;
- `docs/research/project_round538_integration_plan_handoff_status_2026-07-05.md`;
- `docs/research/cn_stock_round533_two_agent_source_tooling_review_2026-07-05.md`.

## Handoff Check

For clean office-topic handoff:

```powershell
.\.venv\Scripts\python.exe scripts\run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready
```

For real integration, only on laptop `main`:

```powershell
python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute
```

## Round543 Output

Round543 should produce:

- a two-agent review document;
- a next-step checklist;
- an index update;
- clear go/no-go decisions for provider, LPR, source-family, branch integration, and further office-desktop work.
