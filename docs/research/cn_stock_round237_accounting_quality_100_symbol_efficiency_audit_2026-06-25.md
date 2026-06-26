# CN Stock Round237 Accounting Quality 100-Symbol Efficiency Audit - 2026-06-25

## Scope

Round237 changes the next action after the Round236 100-symbol accounting-statement node.

The previous next action was to continue shard 6 with two more symbols. That is technically safe, but it is not efficient enough as the default path. The new gate is: first prove the completed 100-symbol statement set can generate the intended accounting-quality formulas, then test whether the backfill throughput can be improved, and only then continue broad data collection.

No profitability result is claimed here. This is a method and data-foundation audit.

## Why The Direction Changed

Completed Round236 coverage:

| Item | Value |
|---|---:|
| Completed subshards | 50 |
| Completed symbols | 100 |
| Full-universe symbols | 5,208 |
| Symbol coverage | 1.9201% |
| Completed endpoint requests | 13,200 |
| Full-universe endpoint requests | 687,456 |
| Endpoint coverage | 1.9201% |
| Remaining endpoint requests | 674,256 |
| Processed statement rows | 4,387 |
| Empty statement requests | 149 |
| Empty-request rate | 1.1288% |

At the current two-symbol subshard shape, the full universe has 2,604 subshards and 2,554 remain. Even under scenario assumptions:

| Scenario | Remaining runtime |
|---|---:|
| 5 minutes per two-symbol subshard | 212.83 hours |
| 9 minutes per two-symbol subshard | 383.10 hours |

This means continuing the ordinary route without a method gate risks spending a large amount of time and Tushare quota before proving the formulas, labels, and portfolio workflow are worth the spend.

## Tool Compatibility Audit

The existing `financial_pit_post_announcement_drift_matrix_label_smoke` path is not directly compatible with this accounting-quality statement line.

Evidence:

- it loads `_load_fina_indicator_inputs`;
- its implemented formula registry is PEAD/announcement-drift oriented;
- its formulas require fields such as `signal_date` and `netprofit_yoy`;
- Round236 statement inputs contain `netprofit`, `n_cashflow_act`, `total_assets`, `total_liab`, `total_cur_assets`, and `total_cur_liab`.

Conclusion: the PEAD/fina_indicator tool can be reused conceptually for PIT discipline and label alignment, but the accounting-quality line needs its own statement-formula smoke or an adapter. Reusing the old tool directly would be a direction error.

## 100-Symbol Statement Formula Smoke

The completed 100-symbol statement set was inspected without using return labels.

| Item | Value |
|---|---:|
| Source roots scanned | 50 |
| Source files scanned | 600 |
| Missing roots | 0 |
| Statement rows before dedup | 4,387 |
| Statement rows after dedup | 4,386 |
| Unique symbols | 100 |
| Unique symbol-report periods | 4,385 |
| Duplicate key rows, `asset_id/end_date/ann_date/report_type` | 1 |
| Announcement date range | 2015-04-18 to 2026-04-30 |
| Report period range | 2015-03-31 to 2025-12-31 |

Formula coverage:

| Candidate formula | Direction | Valid rows | Coverage | Symbols |
|---|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | lower accruals better | 4,286 | 97.72% | 100 |
| `cashflow_minus_netprofit_to_assets_raw` | higher cash conversion better | 4,286 | 97.72% | 100 |
| `low_asset_growth_quality_raw` | lower asset growth better | 3,919 | 89.3525% | 100 |
| `working_capital_accruals_to_assets_raw` | lower working-capital accrual pressure better | 3,836 | 87.4601% | 98 |
| `earnings_cash_conversion_improvement_yoy_raw` | improving cash conversion better | 3,813 | 86.9357% | 100 |

Interpretation:

- The core cashflow/accrual formulas are viable on the existing 100-symbol set.
- Year-over-year formulas naturally start later because they require four-quarter history.
- The one duplicate key row must be deduplicated before any persistent factor matrix or label alignment.
- This smoke is enough to justify building the accounting-quality formula path, but not enough to preregister or promote factors.

Repeatable implementation:

- module: `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`;
- CLI: `scripts/run_accounting_quality_statement_formula_smoke.py`;
- tests: `tests/unit/test_accounting_quality_statement_formula_smoke.py`, `tests/unit/test_accounting_quality_statement_formula_smoke_cli.py`;
- latest local output: `data/reports/round237_accounting_quality_statement_formula_smoke_20260625/accounting_quality_statement_formula_smoke.json`;
- latest result: passed, blockers 0, return labels not used, IC not calculated, promotion blocked.

## Required Round237 Gates

Before more broad backfill:

- run a repeatable statement-accounting-quality formula coverage smoke;
- deduplicate `asset_id/end_date/ann_date/report_type`;
- define PIT signal timing as first tradable date after `ann_date`;
- block same-day close execution from announcement data;
- require at least 30 symbols per cross-section before any IC read;
- log every tested formula and parameter set for multiple-testing control;
- include cost, capacity, listing-status, and regime checks before any promotion discussion;
- keep final holdout untouched.

## Throughput Gate Result

After the repeatable 100-symbol formula smoke passed, a larger statement backfill gate was run on shard 6 offset 0 with `symbol_limit=5`.

| Item | Value |
|---|---:|
| Symbols | 5 |
| Endpoint requests | 660 |
| Max endpoint requests | 900 |
| Processed rows | 220 |
| Empty requests | 0 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Approx wall-clock time | 578 seconds |

Symbols:

- `000428.SZ`
- `000778.SZ`
- `000557.SZ`
- `000426.SZ`
- `000630.SZ`

The same accounting-quality formula smoke was then run on the new 5-symbol output:

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 220 | 100.0% | 5 |
| `cashflow_minus_netprofit_to_assets_raw` | 220 | 100.0% | 5 |
| `low_asset_growth_quality_raw` | 200 | 90.9091% | 5 |
| `working_capital_accruals_to_assets_raw` | 200 | 90.9091% | 5 |
| `earnings_cash_conversion_improvement_yoy_raw` | 200 | 90.9091% | 5 |

Result: the `symbol_limit=5` gate passed with no empty requests, no duplicate statement keys, PIT readiness passed, and formula smoke passed.

Cumulative smoke after adding this gate:

| Item | Value |
|---|---:|
| Source roots | 51 |
| Source files | 612 |
| Statement rows before dedup | 4,607 |
| Statement rows after dedup | 4,606 |
| Unique symbols | 105 |
| Duplicate statement keys | 1 |
| Blockers | 0 |

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,506 | 97.8289% | 105 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,506 | 97.8289% | 105 |
| `low_asset_growth_quality_raw` | 4,119 | 89.4268% | 105 |
| `working_capital_accruals_to_assets_raw` | 4,036 | 87.6248% | 103 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,013 | 87.1255% | 105 |

A second non-overlapping `symbol_limit=5` gate was then run on shard 6 offset 5.

| Item | Value |
|---|---:|
| Symbols | 5 |
| Endpoint requests | 660 |
| Max endpoint requests | 900 |
| Processed rows | 221 |
| Empty requests | 8 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |

Symbols:

- `000612.SZ`
- `000001.SZ`
- `002162.SZ`
- `000505.SZ`
- `000702.SZ`

Formula smoke on the second 5-symbol output:

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 213 | 96.8182% | 5 |
| `cashflow_minus_netprofit_to_assets_raw` | 213 | 96.8182% | 5 |
| `low_asset_growth_quality_raw` | 194 | 88.1818% | 5 |
| `working_capital_accruals_to_assets_raw` | 157 | 71.3636% | 4 |
| `earnings_cash_conversion_improvement_yoy_raw` | 190 | 86.3636% | 5 |

Full cumulative smoke after adding both shard 6 limit-5 gates and the original pilot first2:

| Item | Value |
|---|---:|
| Source roots | 52 |
| Source files | 624 |
| Statement rows before dedup | 4,828 |
| Statement rows after dedup | 4,826 |
| Unique symbols | 110 |
| Duplicate statement keys | 2 |
| Blockers | 0 |

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,719 | 97.7828% | 110 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,719 | 97.7828% | 110 |
| `low_asset_growth_quality_raw` | 4,313 | 89.3701% | 110 |
| `working_capital_accruals_to_assets_raw` | 4,193 | 86.8835% | 107 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,203 | 87.0908% | 110 |

A third non-overlapping `symbol_limit=5` gate was run on shard 6 offset 10.

| Item | Value |
|---|---:|
| Symbols | 5 |
| Endpoint requests | 660 |
| Max endpoint requests | 900 |
| Processed rows | 220 |
| Empty requests | 18 |
| Skipped requests | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |

Symbols:

- `000506.SZ`
- `000938.SZ`
- `600608.SH`
- `000551.SZ`
- `000423.SZ`

Formula smoke on the third 5-symbol output:

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 203 | 92.2727% | 5 |
| `cashflow_minus_netprofit_to_assets_raw` | 203 | 92.2727% | 5 |
| `low_asset_growth_quality_raw` | 190 | 86.3636% | 5 |
| `working_capital_accruals_to_assets_raw` | 190 | 86.3636% | 5 |
| `earnings_cash_conversion_improvement_yoy_raw` | 171 | 77.7273% | 5 |

Full cumulative smoke after adding all three shard 6 limit-5 gates and the original pilot first2:

| Item | Value |
|---|---:|
| Source roots | 53 |
| Source files | 636 |
| Statement rows before dedup | 5,048 |
| Statement rows after dedup | 5,046 |
| Unique symbols | 115 |
| Duplicate statement keys | 2 |
| Blockers | 0 |

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,922 | 97.5426% | 115 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,922 | 97.5426% | 115 |
| `low_asset_growth_quality_raw` | 4,503 | 89.2390% | 115 |
| `working_capital_accruals_to_assets_raw` | 4,383 | 86.8609% | 112 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,374 | 86.6825% | 115 |

## 115-Symbol Matrix Label Smoke

This round added the missing PIT label-alignment gate before any IC or portfolio read.

Command artifact:

- `scripts/run_accounting_quality_statement_matrix_label_smoke.py`
- `data/reports/round238_accounting_quality_statement_matrix_label_smoke_115_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`

Result:

| Item | Value |
|---|---:|
| Statement assets | 115 |
| Statement rows after dedup | 5,046 |
| Duplicate statement keys tracked | 2 |
| Bar assets | 115 |
| Bar rows | 306,210 |
| Factor count | 5 |
| Factor value rows | 22,549 |
| Label rows | 585,163 |
| Label aligned rows | 45,098 |
| Label coverage | 100.00% |
| Alignment violation rows | 0 |
| Horizons | 5, 20 |
| Execution lag | 1 |
| Announcement window | 2015-04-18 to 2025-10-31 |
| Signal-date window | 2015-04-20 to 2025-11-11 |

Candidate label-smoke evidence:

| Candidate formula | Factor rows | Label rows | Coverage | Violations |
|---|---:|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,811 | 9,622 | 100.00% | 0 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,811 | 9,622 | 100.00% | 0 |
| `low_asset_growth_quality_raw` | 4,390 | 8,780 | 100.00% | 0 |
| `working_capital_accruals_to_assets_raw` | 4,273 | 8,546 | 100.00% | 0 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,264 | 8,528 | 100.00% | 0 |

Gate decision: this is a timing and label-readiness pass only. It does not calculate IC, Sharpe, return, or promotion readiness. The next allowed gate is `accounting_quality_statement_residual_ic_shape_prescreen`.

## 115-Symbol Residual IC Shape Prescreen

The next gate was run after label alignment.

Artifact:

- `data/reports/round239_accounting_quality_statement_residual_ic_shape_prescreen_115_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`

Result:

| Item | Value |
|---|---:|
| Candidate formulas | 5 |
| Factor rows | 22,549 |
| Label aligned rows | 45,098 |
| Tests | 10 |
| FDR-significant tests | 0 |
| Neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed | 0 |

Best raw IC rows:

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `low_asset_growth_quality_raw` | 5 | 0.0454 | 0.249 | 1.36 | 56.7% | 0.0093 | 0.8485 | 0.0327 | 0.0524 | reject, no FDR and size/liquidity neutral gates fail |
| `earnings_cash_conversion_improvement_yoy_raw` | 5 | -0.0438 | -0.414 | -2.23 | 24.1% | -0.0045 | 0.5000 | -0.0388 | -0.0428 | reject, wrong sign and no FDR |
| `cashflow_minus_netprofit_to_assets_raw` | 20 | 0.0337 | 0.202 | 1.12 | 58.1% | 0.0022 | 1.0000 | 0.0366 | 0.0370 | reject, no FDR and weak monotonicity |

Interpretation: the original five raw accounting-quality formulas are not ready for walk-forward or portfolio conversion. The next useful work is either broader sample expansion for statistical power, or formula repair into industry-relative/size-neutral accounting-quality composites before retesting.

## Decision

The earlier blind two-symbol continuation is retired as the default action.

Allowed next work:

1. Continue shard 6 from `symbol_offset=15` with `symbol_limit=5`.
2. Expand the accounting-quality sample or repair the raw formulas before another IC gate.
3. Continue larger subshards only when the same PIT readiness and formula-smoke gates pass.
4. Keep formula-smoke and matrix-label-smoke scripts as required pre-mining gates for this family.

Blocked:

- no accounting-quality preregistration from the 100-symbol smoke alone;
- no walk-forward or portfolio conversion for the five raw formulas from the 115-symbol residual IC shape prescreen;
- no portfolio grid until residual IC shape, walk-forward, cost/capacity, and regime coverage checks pass;
- no promotion claim;
- no final holdout access.

## Quant Research Audit

This change directly addresses four failure modes:

- short-sample/regime blindness: do not infer profitability from the 100-symbol smoke;
- look-ahead risk: force signal date after `ann_date`;
- multiple testing: require a tested-hypothesis log before IC/promotion claims;
- capacity/cost fantasy: require cost and liquidity checks before portfolio conclusions.

The correct direction is accounting accruals and cashflow quality for CN stocks, but the correct next step is not unlimited API collection. The correct next step is to prove formula viability, PIT alignment, throughput, and validation gates first.
