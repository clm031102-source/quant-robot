# CN Stock Round241 Accounting Quality Shard6 Completion And 120-Symbol Replay

Date: 2026-06-25

## Objective

Complete the remaining shard6 financial-statement slice and replay accounting-quality gates on the enlarged PIT statement sample. This round is a data-power expansion and gate replay. It is not a portfolio grid, Sharpe, annual-return, win-rate, drawdown, paper-ready, or live-trading claim.

## Inputs

- New backfill slice: shard6, symbol offset 15, symbol limit 5.
- New symbols: `300106.SZ`, `000681.SZ`, `000927.SZ`, `000421.SZ`, `601601.SH`.
- Statement roots after replay: 54.
- Unique statement symbols after replay: 120.
- Bars: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260616_combined_research`.
- Daily-basic context: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260617_daily_basic_factor_inputs`.
- Stock basic: `data/processed/cn_stock_metadata`.

## Backfill Result

| Item | Value |
|---|---:|
| Endpoint requests | 660 |
| Processed rows | 220 |
| Empty requests | 18 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Passes | true |

The cumulative statement sample increased from 115 to 120 symbols.

## Gate Replay Results

| Gate | Result |
|---|---:|
| Formula smoke passes | true |
| Formula source roots | 54 |
| Formula source files | 648 |
| Statement rows before dedup | 5,268 |
| Statement rows after dedup | 5,266 |
| Duplicate statement keys | 2 |
| Unique symbols | 120 |
| Matrix-label smoke passes | true |
| Alignment violations | 0 |
| Factor value rows | 23,455 |
| Label aligned rows | 46,910 |
| Label coverage | 1.0 |

## Residual IC Replay

| Mode | Candidates | Tests | Factor rows | Aligned rows | FDR tests | Neutral-gate tests | Research leads | Promotion allowed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 5 | 10 | 23,455 | 46,910 | 0 | 0 | 0 | 0 |
| repaired | 3 | 6 | 4,929 | 9,858 | 0 | 0 | 0 | 0 |

## Top Rows

| Factor | H | IC | ICIR | t | IC>0 | Q-spread | Monotonicity | Size neutral IC | Liquidity neutral IC | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `low_asset_growth_quality_raw` | 5 | 0.0428 | 0.246 | 1.37 | 61.3% | 0.0098 | 0.50 | 0.0271 | 0.0517 | reject |
| `earnings_cash_conversion_improvement_yoy_raw` | 5 | -0.0405 | -0.357 | -1.92 | 34.5% | -0.0044 | -0.60 | -0.0368 | -0.0407 | reject |
| `aq_repaired_industry_relative_cash_accrual_quality` | 5 | 0.0294 | 0.351 | 1.95 | 51.6% | 0.0021 | 0.30 | -0.0034 | 0.0023 | reject |
| `aq_repaired_industry_relative_cash_accrual_quality` | 20 | 0.0223 | 0.187 | 1.04 | 38.7% | 0.0021 | 0.50 | -0.0006 | -0.0148 | reject |

## Audit

Expanding from 115 to 120 symbols did not create a usable lead. The best raw factor still has a visually interesting 5-day IC, but ICIR is only 0.246, t-stat is 1.37, FDR is false, and monotonicity is weak. The best repaired factor improved to t-stat 1.95, but it still fails FDR, IC positive-rate, monotonicity, and size/liquidity neutral gates.

This means the problem is not a missing TopN, cost setting, or drawdown tolerance. The alpha shape is too weak before portfolio construction. Portfolio conversion here would be data mining.

## Decision

No Round241 accounting-quality candidate is promoted to walk-forward, portfolio grid, paper-ready, or live use.

Allowed next work:

1. Continue PIT statement sample expansion from shard7 offset0 with symbol limit 5.
2. Keep formula smoke, matrix-label smoke, residual IC, FDR, neutralization, regime, cost/capacity, and final-holdout gates.
3. If additional sample expansion still produces zero leads, rotate to a different accounting-quality substructure such as revision surprise, abnormal accrual change, or event-window post-announcement drift.

Blocked:

- no parameter tuning around the five raw accounting-quality formulas;
- no parameter tuning around the three repaired candidates;
- no portfolio grid from Round241;
- no final holdout access;
- no profitability claim.

## Evidence

- Backfill: `data/processed/round241_financial_statement_shard6_offset15_limit5_20260625/financial_statement_shard_backfill.json`
- Formula smoke: `data/reports/round241_accounting_quality_formula_smoke_120_symbol_20260625/accounting_quality_statement_formula_smoke.json`
- Matrix-label smoke: `data/reports/round241_accounting_quality_matrix_label_smoke_120_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`
- Raw prescreen: `data/reports/round241_accounting_quality_raw_prescreen_120_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Repaired prescreen: `data/reports/round241_accounting_quality_repaired_prescreen_120_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
