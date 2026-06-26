# CN Stock Round244 Accounting Quality New Substructure Implementation And Prescreen

Date: 2026-06-25
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock factor validation, research-to-review only

## Purpose

Round244 implemented the first two Round243 accounting-quality new-substructure hypotheses and screened them without mixing them into the stopped raw/repaired cash-accrual family.

Implemented factors:

- `aq_abnormal_accrual_change_reversal`
- `aq_balance_sheet_stress_relief`

The residual IC screen used `factor_mode=new_substructure`, so the old five raw cash/accrual formulas were not counted in this round's IC conclusion.

## Code And Test Changes

Code:

- `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`
- `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

Tests:

- `tests/unit/test_accounting_quality_statement_formula_smoke.py`
- `tests/unit/test_accounting_quality_statement_matrix_label_smoke.py`
- `tests/unit/test_accounting_quality_statement_residual_ic_shape_prescreen.py`

TDD evidence:

- Red test failed because the two new factors were missing from coverage and matrix-label summaries.
- Red test failed because `factor_mode=new_substructure` was unsupported.
- Green tests passed after adding formula registry entries, PIT-safe calculations, and the new residual IC mode.

## Data Gates

Formula smoke report: `data/reports/round244_accounting_quality_new_substructure_formula_smoke_130_symbol_20260625/accounting_quality_statement_formula_smoke.json`

- Passes: true
- Statement symbols: 130
- Statement rows: 5707
- Formula count: 7
- Formulas with values: 7

New formula coverage:

| Factor | Valid rows | Coverage | Symbols |
| --- | ---: | ---: | ---: |
| `aq_abnormal_accrual_change_reversal` | 4910 | 86.0347% | 130 |
| `aq_balance_sheet_stress_relief` | 4852 | 85.0184% | 126 |

Matrix-label report: `data/reports/round244_accounting_quality_new_substructure_matrix_label_smoke_130_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`

- Passes: true
- Factor count: 7
- Factor value rows: 34903
- Label aligned rows: 69806
- Label coverage: 1.0
- Alignment violation rows: 0

New-substructure matrix rows:

| Factor | Factor rows | Label rows | Alignment violations |
| --- | ---: | ---: | ---: |
| `aq_abnormal_accrual_change_reversal` | 4787 | 9574 | 0 |
| `aq_balance_sheet_stress_relief` | 4733 | 9466 | 0 |

## Residual IC Prescreen

Residual IC report: `data/reports/round244_accounting_quality_new_substructure_residual_ic_prescreen_130_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`

Summary:

- Candidate count: 2
- Test count: 4
- Factor rows: 9520
- Aligned rows: 19040
- FDR significant tests: 0
- Neutral gate pass tests: 0
- Research leads: 0
- Promotion allowed candidates: 0

Results:

| Factor | Horizon | IC | ICIR | t-stat | p-value | FDR | Pos IC | Q spread | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `aq_abnormal_accrual_change_reversal` | 5 | -0.0505 | -0.399 | -2.292 | 0.0219 | false | 33.33% | -0.0084 | false |
| `aq_abnormal_accrual_change_reversal` | 20 | -0.0134 | -0.099 | -0.567 | 0.5706 | false | 45.45% | -0.0094 | false |
| `aq_balance_sheet_stress_relief` | 5 | -0.0052 | -0.033 | -0.193 | 0.8466 | false | 52.94% | -0.0029 | false |
| `aq_balance_sheet_stress_relief` | 20 | -0.0035 | -0.022 | -0.129 | 0.8974 | false | 44.12% | -0.0105 | false |

Neutral observations:

- Industry-neutral rows: 90
- Size-neutral rows: 134
- Liquidity-neutral rows: 134
- Neutral gate pass count: 0

## Interpretation

No Round244 factor is useful enough for walk-forward or portfolio conversion.

The only notable data point is `aq_abnormal_accrual_change_reversal` at 5 days: raw IC is negative with unadjusted p-value below 0.05. This is not a lead because it failed FDR, ICIR, positive-rate, quantile spread, and neutral gates. It may be a sign-direction problem or noise. Treating the inverse as a discovery would be data snooping unless it is preregistered and counted as a new hypothesis in Round245.

`aq_balance_sheet_stress_relief` has a positive 5-day industry-neutral IC, but the t-stat is only 1.53 and size/liquidity-neutral ICs are negative. It is not robust.

## Decision

- New factors implemented: 2
- New validated/useful factors: 0
- New promotable factors: 0
- New walk-forward candidates: 0
- Directional audit candidates: 1, only as a preregistered next test

Next direction:

`round245_accounting_quality_new_substructure_directional_audit_or_family_rotation`

Round245 should either preregister a directional audit for `aq_abnormal_accrual_change_reversal` or rotate to another Round243 seed such as post-statement announcement drift or profitability revision surprise. Portfolio grids, final holdout, and live/paper claims remain blocked.
