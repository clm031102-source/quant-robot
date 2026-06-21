# Round94 Fina Indicator First10 Shard Smoke Plan

## Steps

1. Add a reusable shard-smoke entrypoint that reads a shard plan and selects first N symbols.
2. Verify the entrypoint with TDD:
   - firstN symbol selection;
   - request-budget blocker;
   - limited backfill smoke output;
   - PIT readiness output.
3. Run Round94 on shard 1 first 10 symbols:
   - shard plan: `data/reports/fina_indicator_symbol_shard_plan_round93_20260621/fina_indicator_symbol_shard_plan.json`;
   - max symbols: 10;
   - max requests: 440;
   - output: `data/processed/tushare_fina_indicator_shard1_first10_backfill_smoke_round94_20260622`;
   - PIT report: `data/reports/tushare_financial_pit_readiness_round94_shard1_first10_20260622`.
4. Inspect quality report:
   - processed rows;
   - empty requests;
   - duplicate rows;
   - missing asset ids;
   - missing numeric fields;
   - date ranges.
5. If duplicate rows appear, write a failing test and fix ingestion before accepting the round.
6. Write Round94 research report and update startup gate.
7. Run verification commands.

## Stop Conditions

- Stop full-shard expansion if duplicate rows remain above 0.
- Stop profitability factor pre-registration until broader PIT financial coverage exists.
- Stop if PIT readiness fails.
