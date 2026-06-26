# Round95 Fina Indicator Shard1 Full100 Backfill Plan

## Steps

1. Run the reusable shard backfill entrypoint on shard 1 with 100 symbols.
2. Keep the request budget explicit:
   - shard plan: `data/reports/fina_indicator_symbol_shard_plan_round93_20260621/fina_indicator_symbol_shard_plan.json`;
   - shard id: 1;
   - max symbols: 100;
   - periods: 44;
   - max requests: 4,400.
3. Capture runtime and stderr/stdout logs under `data/reports/round95_shard1_full100_run_20260622`.
4. Inspect output quality:
   - processed rows;
   - empty requests;
   - duplicate rows;
   - missing asset ids;
   - missing numeric fields;
   - announcement and report-period ranges.
5. Inspect PIT readiness output and require no blockers.
6. Write Round95 research report and cumulative work report.
7. Update startup gate to point Round96 at profitability-quality pre-registration and coverage audit.
8. Run verification commands.

## Stop Conditions

- Stop factor pre-registration if duplicate rows are above 0.
- Stop factor pre-registration if missing asset ids are above 0.
- Stop factor pre-registration if PIT readiness fails.
- Stop factor promotion from this single shard even if coverage is clean.
