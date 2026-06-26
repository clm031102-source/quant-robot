# Round91 Fina Indicator Backfill Design

## Goal

Build a planning-only guardrail for long-history Tushare `fina_indicator` backfill before any profitability or quality factor can be pre-registered.

## Context

Round88 found that the existing CN stock local roots had no PIT-ready profitability dataset. Round89 proved the fixture `fina_indicator` shape, and Round90 proved one real symbol-scoped Tushare `fina_indicator` request can be ingested with `ann_date` and `end_date`. The next failure mode to avoid is jumping from a one-symbol smoke test into full profitability factor mining without a long-cycle, resume-safe, rate-limited backfill plan.

## Selected Approach

Use a planning-first implementation:

- Generate quarter-end periods from `2015-03-31` through `2025-12-31`.
- Accept an explicit symbol list or symbol file.
- Estimate total Tushare requests as `symbols * quarters`.
- Split requests into deterministic batches.
- Record resume, rate-limit, no-data-commit, and no-live-boundary safety flags.
- Write JSON and Markdown plan artifacts under `data/reports/...`.
- Do not call Tushare from the planner.
- Do not generate raw or processed market data.

This is preferable to immediate full backfill because it makes request volume, batching, and safety blockers visible before consuming API quota or creating large local artifacts.

## Rejected Approaches

- Immediate all-symbol live backfill: too large without a request budget, rate-limit estimate, and resume plan.
- Profitability factor pre-registration from the one-symbol Round90 smoke: statistically meaningless and likely to create false confidence.
- Reusing daily-basic valuation proxies as profitability: already rejected because they do not provide PIT financial statement evidence.

## Components

- `src/quant_robot/ops/fina_indicator_backfill_plan.py`: pure planning logic and Markdown renderer.
- `scripts/run_fina_indicator_backfill_plan.py`: CLI that writes the plan artifacts.
- `tests/unit/test_fina_indicator_backfill_plan.py`: unit tests for period generation, batching, and blockers.
- `tests/unit/test_fina_indicator_backfill_plan_cli.py`: CLI artifact smoke tests.
- `docs/research/cn_stock_tushare_fina_indicator_backfill_plan_round91_2026-06-21.md`: research report for the round.
- `configs/factor_mining_startup_cn_stock.json`: advance the repeatable protocol to the next safe step after this planner is verified.

## Safety

The planner is research-to-review only. It does not connect to brokers, read accounts, place orders, or do live trading. It also does not write secrets, tokens, raw market data, processed market data, or large outputs to Git.

## Success Criteria

- Planner returns 44 quarterly report periods for 2015-03-31 through 2025-12-31.
- For two symbols, request count is 88 and batch count is deterministic.
- If request count exceeds a configured budget, the plan records a blocker.
- CLI writes both JSON and Markdown artifacts.
- Startup gate can still clear after recording the next direction.
- Focused tests and project audit pass.
