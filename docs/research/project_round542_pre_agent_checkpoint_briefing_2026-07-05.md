# Project Round542 Pre-Agent Checkpoint Briefing

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 39 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, did not touch final holdout, did not push `main`, and did not delete any remote branch. It prepared the Round543 two-agent review checkpoint.

## Round Objective

Round543 is the next required two-agent checkpoint after Round533. Round542 prepares a concise state package so the Quant PM reviewer and ordinary-user reviewer can focus on decision quality instead of rediscovering the latest branch, provider, source, and handoff state.

## Fresh Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 06:04:23 +08:00.
- Current branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Current topic head: `253e48d7`.
- Git status before work: clean and synchronized with origin.
- Remote branches: `origin/main` at `af474d5a`, active topic at `253e48d7`.
- Topic/main relationship: `0 39`.
- Startup context: branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.
- Tracked generated data paths under `data/raw`, `data/processed`, and `data/reports`: none.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Integration Handoff State

Current laptop integration plan summary:

- `status=blocked`;
- blocker: `current_branch_must_be_main`;
- `handoff.status=ready_on_main`;
- `handoff.next_command=python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute`;
- merge order commit: `253e48d79e85fd67381cc0f0ee658607d80201c0`.

Interpretation:

- The office topic branch is ready to hand off.
- The real merge remains laptop-owned and must run from laptop on `main`.
- Office desktop should not push `main` or delete the active remote branch.

## Research State For Reviewers

Analyst-report-revision path:

- January-March 2024 cache and screening evidence exists.
- April cache remains blocked until provider quota and required-machine evidence clear.
- Required quota pack machines remain `office_desktop`, `highspec_desktop`, and `laptop`.
- Missing required quota packs remain `highspec_desktop` and `laptop` unless new external packs are imported.
- Frozen January-April prescreen should run exactly once only after April cache succeeds.
- No final holdout.

External-feed/LPR path:

- HK-hold source coverage and join-smoke evidence are source-quality evidence only.
- Old northbound accumulation remains hibernated.
- Old northbound crowding/reversal remains hibernated.
- Margin-credit remains hibernated.
- LPR/macro factors remain blocked until plausible LPR cache evidence, offline repair, and coverage audit pass.
- SHIBOR may be reviewed only as a regime-control input after long-cycle validation.

Branch/main state:

- Cloud branch structure is minimal: stable `main` plus one active topic branch.
- `--require-handoff-ready` now gives a machine-checkable office handoff signal.
- Do not continue manual merge rehearsal documents by default unless code/config/integration state changes or the handoff gate fails.

## Round543 Review Questions

Quant PM reviewer should answer:

- Is it better to keep waiting for laptop mainline integration, import missing quota packs, or continue non-provider source-tooling hardening?
- Are any source families incorrectly reopened despite prior hibernation evidence?
- Does the project have any legitimate factor-research action before analyst quota/LPR blockers clear?
- Are the current handoff and branch boundaries sufficient for project quality?

Ordinary-user reviewer should answer:

- Can a non-expert tell what to run next and where to run it?
- Is `ready_on_main` clear enough, or does it still look executable from office desktop?
- Are provider/data commands still too easy to copy accidentally?
- Is the current checklist too long, stale, or confusing?

## Decision

Round543 should create two fresh reviewers:

- Quant PM reviewer for portfolio/source/process decision quality.
- Ordinary-user reviewer for usability and operator-mistake risk.

The default action before their review remains non-provider and non-merge from office desktop.

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
