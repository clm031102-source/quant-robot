# CN Stock Round235-236 Accounting-Quality Statement Backfill - 2026-06-25

## Scope

Machine/task context:

- machine: `office_desktop`;
- task: `factor_validation`;
- branch: `codex/factor-validation-cn-stock-long-cycle-20260618`;
- market/asset: CN stock;
- research-only: no broker, no account reads, no orders, no live trading.

This round does not promote any factor. It fixes the data and method gate required before accounting-quality factors can be pre-registered.

## Problem Fixed

Round234 selected accounting accruals and cash-flow quality as the next high-rationale family, but the local data only had `fina_indicator` style profitability ratios. Real accounting-quality anomalies need PIT-safe statement fields from income, balance sheet, and cash-flow statements.

The previous readiness gate also had a bug: it treated "PIT ready" as "has PIT dates and ROE/ROA-style profitability columns". That incorrectly rejected financial statement datasets that have PIT dates and the required accounting fields but no profitability-ratio columns.

## Implementation

Added Tushare statement support:

- `TushareAdapter.fetch_income_statement`
- `TushareAdapter.fetch_balance_sheet`
- `TushareAdapter.fetch_cashflow_statement`
- statement mapping in `src/quant_robot/data/sources/tushare_mapping.py`
- combined PIT statement ingest in `src/quant_robot/data/ingest/tushare_financial_statements.py`
- limited statement smoke CLI: `scripts/run_financial_statement_limited_backfill_smoke.py`
- full-universe statement shard plan CLI: `scripts/run_financial_statement_symbol_shard_plan.py`

Readiness gate fix:

- required column groups now evaluate against PIT-date-ready financial datasets;
- ROE/ROA-style profitability columns are still required for the old profitability readiness mode;
- accounting statement readiness can pass with `netprofit`, `n_cashflow_act`, and `total_assets` even without ROE/ROA columns.

Official Tushare endpoint references checked:

- `income`: https://tushare.pro/wctapi/documents/33.md
- `balancesheet`: https://tushare.pro/wctapi/documents/36.md
- `cashflow`: https://tushare.pro/wctapi/documents/44.md

## Required Fields

Current forward gate:

| Group | Required fields |
|---|---|
| `accounting_accrual_quality` | `netprofit`, `n_cashflow_act`, `total_assets` |
| `asset_growth_quality` | `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab` |

These fields support accruals quality, cash-flow conversion, asset growth, and working-capital accruals. `ocfps` is no longer the forward gate for the accounting accrual group because the real statement formula should use operating cash flow and total assets directly.

## Round235 Limited Smoke

Command:

```powershell
python scripts\run_financial_statement_limited_backfill_smoke.py --symbols 000001.SZ,600519.SH --start-period 2024-03-31 --end-period 2024-06-30 --batch-size 10 --max-endpoint-requests 20 --output-dir data\processed\round235_financial_statement_limited_smoke_20260625
```

Result:

| Metric | Value |
|---|---:|
| Symbols | 2 |
| Periods | 2 |
| Endpoint requests | 12 |
| Processed rows | 4 |
| Empty requests | 0 |
| Required groups passing | 2 / 2 |

The standalone readiness audit on the smoke output also passed: 16 files scanned, 14 financial-like datasets, 13 PIT-ready datasets, 2 / 2 required groups passing.

## Round236 Full-Universe Plan

Command:

```powershell
python scripts\run_financial_statement_symbol_shard_plan.py --stock-basic-root data\processed\cn_stock_metadata\metadata\tushare_stock_basic --start-period 2015-03-31 --end-period 2025-12-31 --symbols-per-shard 20 --max-endpoint-requests-per-shard 3000 --exclude-suffixes BJ --stratify-by industry,exchange,list_year --output-dir data\reports\round236_financial_statement_symbol_shard_plan_20260625
```

Result:

| Metric | Value |
|---|---:|
| Included symbols | 5,208 |
| Excluded BJ symbols | 321 |
| Periods | 44 |
| Endpoint count per symbol-period | 3 |
| Shards | 261 |
| Symbols per shard | 20 |
| Total base requests | 229,152 |
| Total endpoint requests | 687,456 |
| Max endpoint requests per shard | 3,000 |
| Stratification strata | 2,180 |

The plan passed with no blockers. Because the full job is large, the safe execution policy is shard-by-shard or subshard-by-subshard, with resume and readiness audit after each shard.

## Round236 Long-Cycle Pilot

Command:

```powershell
python scripts\run_financial_statement_limited_backfill_smoke.py --symbols 000066.SZ,300029.SZ --start-period 2015-03-31 --end-period 2025-12-31 --batch-size 100 --max-endpoint-requests 300 --output-dir data\processed\round236_financial_statement_pilot_first2_fullcycle_20260625
```

Result:

| Metric | Value |
|---|---:|
| Symbols | 2 |
| Periods | 44 |
| Endpoint requests | 264 |
| Processed rows | 88 |
| Empty requests | 1 |
| Required groups passing | 2 / 2 |
| Ann date range | 2015-04-28 to 2026-04-30 |
| Report period range | 2015-03-31 to 2025-12-31 |

Standalone readiness audit:

| Metric | Value |
|---|---:|
| Files scanned | 279 |
| Financial-like datasets | 277 |
| PIT-ready datasets | 276 |
| Required groups passing | 2 / 2 |
| Blockers | none |

## Current Decision

No accounting-quality factor is pre-registered yet. The data path is proven on small and long-cycle pilots, but full-universe coverage is not complete.

The next valid direction is:

```text
round236_accounting_quality_statement_full_universe_shard_backfill_before_preregistration
```

Allowed next work:

1. Execute one shard or smaller subshard from the Round236 plan.
2. Run statement readiness after each shard.
3. Track empty requests and duplicate rows.
4. Only after full-universe statement readiness passes, pre-register accounting-quality factors.

Forbidden:

- direct factor generation after only the limited smoke;
- portfolio grid before residual IC/shape/dedup gates;
- promotion before long-cycle, walk-forward, cost, capacity, regime, multiple-testing, and final-holdout gates.

## Verification

Commands run:

```powershell
python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_financial_statement_ingest tests.unit.test_financial_statement_limited_backfill_smoke_cli
python -m unittest tests.unit.test_tushare_financial_pit_readiness tests.unit.test_tushare_financial_pit_readiness_cli
python -m unittest tests.unit.test_financial_statement_symbol_shard_plan tests.unit.test_financial_statement_symbol_shard_plan_cli
```

All listed tests passed.
