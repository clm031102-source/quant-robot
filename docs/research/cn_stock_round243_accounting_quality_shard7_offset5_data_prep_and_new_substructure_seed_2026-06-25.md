# CN Stock Round243 Accounting Quality Shard7 Offset5 Data Prep And New Substructure Seed

Date: 2026-06-25
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock factor validation, research-to-review only

## Purpose

Round243 was a process-correction round, not an alpha-promotion round. After Round242 showed zero research leads for the raw and repaired cash-accrual family across 115, 120, and 125 symbol replays, this round intentionally avoided rerunning the same IC screen. The work expanded PIT statement coverage by one more five-symbol slice and registered a new accounting-quality substructure seed for the next mining round.

## Startup And Data Manifest

Startup gate: passed in `data/reports/round243_factor_mining_startup_gate_20260625/factor_mining_startup_gate.json`.

CN stock data manifest: `review_required` with no blockers in `data/reports/round243_cn_stock_data_manifest_20260625/cn_stock_data_manifest.json`.

Manifest warnings remain active evidence boundaries:

- `extreme_return_rows_present`
- `adjusted_ratio_jump_rows_present`
- `adjusted_ratio_mass_jump_dates_present`
- `moneyflow_symbol_coverage_below_bars`
- `daily_basic_symbol_coverage_below_bars`
- `daily_basic_date_coverage_before_bars`

These warnings mean promotion still requires tradeability, price-basis, coverage, regime, and cost/capacity checks.

## Shard7 Offset5 Backfill

Backfill report: `data/processed/round243_financial_statement_shard7_offset5_limit5_20260625/financial_statement_shard_backfill.json`

Selected symbols:

- `000619.SZ`
- `000048.SZ`
- `000816.SZ`
- `000553.SZ`
- `000793.SZ`

Result:

- Passes: true
- Endpoint requests: 660
- Processed rows: 220
- Empty endpoint responses: 7
- Required column groups passing: 2 of 2
- Readiness blockers: 0

Slice formula smoke report: `data/reports/round243_accounting_quality_statement_formula_smoke_shard7_offset5_limit5_20260625/accounting_quality_statement_formula_smoke.json`

Slice formula result:

- Passes: true
- Source files: 12
- Statement rows before dedup: 220
- Statement rows after dedup: 220
- Duplicate statement keys: 0
- Unique symbols: 5

## 130-Symbol Cumulative Readiness

Cumulative formula report: `data/reports/round243_accounting_quality_formula_smoke_130_symbol_20260625/accounting_quality_statement_formula_smoke.json`

Formula smoke:

- Passes: true
- Source roots: 56
- Source files: 672
- Statement rows before dedup: 5709
- Statement rows after dedup: 5707
- Unique symbols: 130
- Duplicate statement keys: 2

Formula coverage:

| Formula | Valid rows | Coverage | Symbols |
| --- | ---: | ---: | ---: |
| `(netprofit - n_cashflow_act) / total_assets` | 5541 | 97.0913% | 130 |
| `(n_cashflow_act - netprofit) / total_assets` | 5541 | 97.0913% | 130 |
| `-pct_change_4q(total_assets)` | 5084 | 89.0836% | 130 |
| `delta_4q(total_cur_assets - total_cur_liab) / total_assets` | 4926 | 86.3151% | 126 |
| `delta_4q((n_cashflow_act - netprofit) / total_assets)` | 4910 | 86.0347% | 130 |

Matrix-label report: `data/reports/round243_accounting_quality_matrix_label_smoke_130_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`

Matrix-label result:

- Passes: true
- Statement assets: 130
- Bar assets: 130
- Factor value rows: 25383
- Label aligned rows: 50766
- Label coverage: 1.0
- Alignment violation rows: 0
- Horizons: 5, 20
- Execution lag: 1
- Signal window: 2015-04-20 to 2025-11-11

## Old-Family Decision

Old raw/repaired cash-accrual IC replay was intentionally skipped.

Reason:

- Round239 raw 115-symbol replay: zero research leads.
- Round240 repaired 115-symbol replay: zero research leads.
- Round241 raw/repaired 120-symbol replay: zero research leads.
- Round242 raw/repaired 125-symbol replay: zero research leads.

Decision:

- Do not treat coverage growth from 125 to 130 symbols as a reason to retune the same failed family.
- Do not run portfolio grids on raw or repaired cash-accrual formulas.
- Do not use final holdout.
- Next IC work must implement a new economic substructure first.

## New Seed Registered

Seed config: `configs/accounting_quality_new_substructure_seed_round243_20260625.json`

New candidate ideas:

- `aq_abnormal_accrual_change_reversal`
- `aq_profitability_revision_surprise`
- `aq_post_statement_announcement_drift`
- `aq_balance_sheet_stress_relief`
- `aq_industry_relative_margin_acceleration`

These are hypotheses only. They are not validated factors yet.

## Process Optimization Written Into The Project

The next mining round must check these controls before any promotion claim:

- A-share tradeability: limit up/down, suspension, ST, new listings, delisting risk, and board permission constraints.
- Financial PIT timing: announcement date, revised announcement, filing lag, first tradable signal date, and no report-period-end signal.
- Industry/style neutralization: industry, size, value, low-vol, momentum, and liquidity residual metrics.
- Portfolio construction: risk budget, volatility target, industry constraints, turnover constraints, cost/capacity, and de-risk rules.
- Strict statistics: Deflated Sharpe, CPCV, White Reality Check, parameter sensitivity heatmaps, overlap-adjusted statistics, and multiple testing logs.
- China market regime: policy, credit cycle, northbound flow, margin financing balance, turnover temperature, and index location.
- Event context: earnings guidance, dividend/ex-right, buyback, shareholder change, lockup expiry, and index rebalance.

## Round243 Scorecard

- New validated factors: 0
- New useful/promotable factors: 0
- New hypothesis seeds registered: 5
- Data readiness expanded: 125 to 130 symbols
- Label alignment violations: 0
- Old failed family rerun: 0

This is a necessary direction correction. The useful output is not a profit signal yet; it is a reusable gate that prevents the next mining round from wasting time on the same failed cash-accrual parameter drift.

## Next Round

Round244 should implement one or more of the new accounting-quality substructure formulas, then run PIT formula smoke, matrix-label smoke, residual IC shape prescreen, and neutralized diagnostics. Only candidates that survive those gates should move toward walk-forward, cost/capacity, regime coverage, and strict statistical reality checks.
