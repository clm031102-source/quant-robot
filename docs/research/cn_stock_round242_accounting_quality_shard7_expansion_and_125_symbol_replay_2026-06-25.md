# CN Stock Round242 Accounting Quality Shard7 Expansion And 125-Symbol Replay

Date: 2026-06-25
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN A-share stock factor validation, research-to-review only

## Objective

Round242 added the first shard7 five-symbol statement slice and replayed the accounting-quality gates on the enlarged point-in-time sample. The purpose was not to force a portfolio backtest, but to check whether the raw and repaired cash/accrual accounting-quality family becomes statistically useful after the sample expands from 120 to 125 symbols.

## Startup And Data Boundary

Startup gate cleared for `office_desktop`, `factor_validation`, CN stock scope, and research-only safety.

The CN stock data manifest had no blockers, but kept the existing review warnings:

- `extreme_return_rows_present`
- `adjusted_ratio_jump_rows_present`
- `adjusted_ratio_mass_jump_dates_present`
- `moneyflow_symbol_coverage_below_bars`
- `daily_basic_symbol_coverage_below_bars`
- `daily_basic_date_coverage_before_bars`

These warnings are evidence boundaries. They do not block this statement-based IC prescreen, but they must be addressed before any promotion, portfolio conversion, or live-facing conclusion.

## Shard7 Offset0 Backfill

New symbols:

- `000509.SZ`
- `000014.SZ`
- `600611.SH`
- `603569.SH`
- `000056.SZ`

Backfill result:

- `passes=true`
- symbols: 5
- endpoint requests: 660
- processed rows: 221
- empty requests: 15
- required column groups passing: 2 of 2
- readiness blockers: 0

Slice formula smoke:

- `passes=true`
- statement rows: 221
- duplicate keys: 0
- formulas with values: 5

## 125-Symbol Replay

Cumulative formula smoke:

- source roots: 55
- source files: 660
- statement rows before dedup: 5,489
- statement rows after dedup: 5,487
- duplicate statement keys: 2
- unique symbols: 125
- formulas with values: 5

Formula coverage:

| Factor | Valid Rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 5,328 | 97.1022% | 125 |
| `cashflow_minus_netprofit_to_assets_raw` | 5,328 | 97.1022% | 125 |
| `low_asset_growth_quality_raw` | 4,887 | 89.0651% | 125 |
| `working_capital_accruals_to_assets_raw` | 4,729 | 86.1855% | 121 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,720 | 86.0215% | 125 |

Matrix-label smoke:

- `passes=true`
- statement assets: 125
- bar assets: 125
- bar rows: 333,052
- factor value rows: 24,398
- label rows: 636,459
- label aligned rows: 48,796
- label coverage: 1.0
- alignment violations: 0
- signal window: 2015-04-20 to 2025-11-11

## IC Prescreen Results

Raw candidates:

- candidate count: 5
- tests: 10
- factor rows: 24,398
- aligned rows: 48,796
- FDR-significant tests: 0
- neutral-gate passes: 0
- research leads: 0
- promotion-allowed candidates: 0

Best raw positive economic candidate:

- `low_asset_growth_quality_raw`, H5
- mean IC: 0.0411
- ICIR: 0.2426
- t-stat: 1.4558
- IC positive rate: 55.56%
- quantile spread: 0.0083
- FDR significant: false
- research lead: false

Largest absolute raw IC was not useful:

- `earnings_cash_conversion_improvement_yoy_raw`, H5
- mean IC: -0.0502
- ICIR: -0.4073
- t-stat: -2.3395
- IC positive rate: 33.33%
- quantile spread: -0.0082
- FDR significant: false
- research lead: false

Repaired candidates:

- candidate count: 3
- tests: 6
- factor rows: 5,601
- aligned rows: 11,202
- FDR-significant tests: 0
- neutral-gate passes: 0
- research leads: 0
- promotion-allowed candidates: 0

Best repaired candidate:

- `aq_repaired_industry_relative_cash_accrual_quality`, H20
- mean IC: 0.0276
- ICIR: 0.2297
- t-stat: 1.3784
- IC positive rate: 52.78%
- quantile spread: -0.0011
- FDR significant: false
- research lead: false

## Decision

The 125-symbol replay confirms the same conclusion as the 115-symbol and 120-symbol replays: this raw/repaired cash-accrual accounting-quality family has no promotable or research-worthy signal under the current residual IC shape gates.

Do not run portfolio grids, walk-forward conversion, or final holdout for these raw/repaired candidates. The next productive action is to rotate within accounting quality to a different substructure:

- earnings revision or guidance surprise after real announcement availability
- abnormal accrual change rather than level accrual formulas
- post-announcement drift event windows
- industry-relative profitability change paired with balance-sheet stress
- regime-conditional accounting signal, explicitly audited for single-regime dependence

Statement backfill can continue as data preparation, but it should not be treated as another same-formula mining retry unless a new hypothesis family is introduced.

## Reusable Rule Added

After three consecutive enlarged-sample replays with 0 FDR tests, 0 neutral-gate passes, and 0 research leads, the current formula family must stop parameter tuning and rotate to a new candidate substructure before any further mining budget is spent on that family.

Safety remains research-to-review only: no broker connection, no account reads, no order placement, no live trading.
