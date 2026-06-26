# CN Stock Round239 Accounting Quality Residual IC Shape Prescreen

Date: 2026-06-25

## Objective

Run the first IC-quality gate after the accounting-quality PIT formula smoke and matrix-label smoke. This is a residual IC shape prescreen only: no Sharpe, total return, annual return, win rate, max drawdown, portfolio grid, promotion, or final-holdout claim.

## Inputs

- Statement roots: 53 completed roots, 115 unique CN stock symbols.
- Bars: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260616_combined_research`.
- Daily-basic context: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260617_daily_basic_factor_inputs`.
- Stock basic: `data/processed/cn_stock_metadata`.
- Report: `data/reports/round239_accounting_quality_statement_residual_ic_shape_prescreen_115_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`.

## Result

| Item | Value |
|---|---:|
| Candidates | 5 |
| Factor rows | 22,549 |
| Label rows | 585,163 |
| Aligned rows | 45,098 |
| Tests | 10 |
| FDR-significant tests | 0 |
| Neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |

## Top Rows

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `low_asset_growth_quality_raw` | 5 | 0.0454 | 0.249 | 1.36 | 56.7% | 0.0093 | 0.8485 | 0.0327 | 0.0524 | reject |
| `earnings_cash_conversion_improvement_yoy_raw` | 5 | -0.0438 | -0.414 | -2.23 | 24.1% | -0.0045 | 0.5000 | -0.0388 | -0.0428 | reject |
| `cashflow_minus_netprofit_to_assets_raw` | 20 | 0.0337 | 0.202 | 1.12 | 58.1% | 0.0022 | 1.0000 | 0.0366 | 0.0370 | reject |
| `low_total_accruals_to_assets_raw` | 20 | -0.0337 | -0.202 | -1.12 | 41.9% | -0.0029 | -1.0000 | -0.0366 | -0.0370 | reject |
| `low_asset_growth_quality_raw` | 20 | 0.0334 | 0.143 | 0.78 | 60.0% | 0.0010 | -0.1818 | 0.0277 | 0.0390 | reject |

## Audit

The raw formulas have weak evidence after multiple-testing accounting. The best raw IC is visually interesting but not statistically clean: `low_asset_growth_quality_raw` at 5 days has IC 0.0454, but ICIR is only 0.249, t-stat is 1.36, FDR is false, quantile monotonicity is 0.50, and size/liquidity neutral gates fail.

This is a useful failure. It says not to spend compute on portfolio conversion yet. The next work should either expand the sample for power or repair the family into industry-relative, size-neutral, cash-conversion and accrual-quality composites before rerunning the same gate.

## Follow-Up Repaired Candidate Check

Round240 executed the first repaired-candidate rerun:

- Report: `data/reports/round240_accounting_quality_repaired_candidate_prescreen_115_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Candidate formulas: 3
- Tests: 6
- Factor rows: 4,552
- Label aligned rows: 9,104
- FDR-significant tests: 0
- Neutral-gate pass tests: 0
- Research leads: 0

Best repaired row: `aq_repaired_industry_relative_cash_accrual_quality`, 5-day IC 0.0291, ICIR 0.328, t-stat 1.67. It still fails FDR, positive-rate, quantile-spread, monotonicity, and neutral gates.

Updated audit: simple repaired accounting-quality composites are not enough on the 115-symbol sample. Do not tune around these three formulas; either expand the PIT statement sample for power or rotate to a different accounting-quality substructure.

## Decision

No raw accounting-quality factor is promoted to walk-forward, portfolio grid, paper-ready, or live use.

Allowed next work:

1. Continue statement backfill as data expansion under the same PIT readiness, formula-smoke, and matrix-label-smoke gates.
2. Design repaired accounting-quality factors: industry-relative asset growth, accruals adjusted for size/liquidity, and composite cash-conversion quality.
3. Rerun residual IC shape prescreen only after expanded data or repaired formulas exist.

Blocked:

- no Sharpe/profit/win-rate claim from this prescreen;
- no portfolio conversion for the five raw formulas;
- no final holdout access.
