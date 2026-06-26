# CN Stock Round271 Financial Reporting Timeliness Backfill Audit

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-round271-financial-timeliness-20260626
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round270 blocked financial reporting timeliness factor generation because local PIT financial sources covered only small samples. Round271 therefore did not generate factors. It tested whether the full-market financial-statement backfill path is viable, corrected the source audit coverage accounting, and advanced coverage with new long-cycle PIT shards.

## Startup Gate

- Startup gate: cleared after renaming the branch to the required `codex/factor-validation-cn-stock-*` prefix.
- Required direction: `round271_financial_reporting_timeliness_backfill_or_retire_before_factor_generation`.
- Candidate generation: blocked until source coverage clears.
- Portfolio grid and promotion: blocked.

## Engineering Fixes

The first Round271 backfill attempt exposed a merge-integration break: `tushare_financial_statements.py` imported financial statement mapping constants that were missing from the current `tushare_mapping.py`.

Fixed:

- restored Tushare financial indicator and income/balance/cashflow mapping contracts;
- restored Tushare adapter methods for financial statements, fina_indicator, tradeability feeds, index weight, external feeds, and dragon-tiger endpoints;
- restored `stock_basic` industry/area/list-date metadata fields;
- added rate-limit-safe request throttling to `TushareAdapter`;
- added CLI throttling options to `scripts/run_financial_statement_shard_backfill.py`;
- corrected `financial_reporting_timeliness_source_audit` to evaluate aggregate union coverage across many shard roots instead of only the largest individual root.

## Backfill Evidence

Two non-overlapping shard segments were completed with request throttling:

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Readiness |
|---|---:|---:|---:|---:|---|
| shard 7 offset 10 limit 5 | 5 | 660 | 220 | 0 | passed |
| shard 7 offset 15 limit 5 | 5 | 660 | 220 | 0 | passed |
| total | 10 | 1,320 | 440 | 0 | passed |

Both segments passed the required PIT column groups:

- `accounting_accrual_quality`: `netprofit`, `n_cashflow_act`, `total_assets`;
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`.

## Source Audit After Shard 7

The aggregate source audit now uses union coverage across all supplied roots.

Output: `data/reports/round271_financial_reporting_timeliness_source_audit_after_shard7_complete_20260626`

| Metric | Value |
|---|---:|
| Sources scanned | 61 |
| Aggregate rows | 39,265 |
| Aggregate unique symbols | 195 |
| Minimum required symbols | 1,000 |
| Minimum required end years | 8 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

Blocker:

- `unique_symbol_count_below_minimum`

The earlier `end_year_coverage_below_minimum` blocker disappeared once the audit used aggregate coverage correctly. Long-cycle coverage is viable; cross-sectional symbol coverage remains insufficient.

## Decision

Continue the backfill route. Do not generate financial reporting timeliness factors yet.

This direction is not retired because:

- the Tushare ordinary statement endpoint route works;
- rate-limit-safe throttling can complete shards without manual timing;
- PIT readiness passes for the completed segments;
- aggregate audit now measures progress correctly.

This direction remains blocked because:

- 195 symbols is far below the 1,000-symbol minimum;
- no IC, portfolio, promotion, or final holdout claim is allowed from this coverage level;
- the current work is data foundation, not alpha discovery.

## Next Action

Round272 should continue from the next non-overlapping subshard:

```text
shard_id=8, symbol_offset=0, symbol_limit=5
```

Use throttled execution:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 8 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 700 --adapter-max-retries 6 --adapter-retry-sleep-seconds 20 --adapter-request-sleep-seconds 0.36 --output-dir data\processed\round272_financial_statement_shard8_offset0_limit5_20260626
```

Continue blocking:

- financial reporting timeliness candidate preregistration;
- IC and portfolio grids;
- promotion claims;
- final holdout access;
- any same-family factor generation before aggregate coverage reaches at least 1,000 symbols.

## Verification

Passed:

```powershell
python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_financial_inputs_ingest tests.unit.test_tushare_financial_statement_ingest tests.unit.test_financial_statement_shard_backfill_cli
python -m unittest tests.unit.test_financial_reporting_timeliness_source_audit tests.unit.test_financial_reporting_timeliness_source_audit_cli
python -m py_compile src\quant_robot\data\sources\tushare_mapping.py src\quant_robot\data\adapters\tushare_adapter.py src\quant_robot\data\ingest\tushare_financial_statements.py scripts\run_financial_statement_shard_backfill.py src\quant_robot\ops\financial_reporting_timeliness_source_audit.py scripts\run_financial_reporting_timeliness_source_audit.py
```

