# CN Stock Round245 Accounting Quality Directional Audit

Date: 2026-06-25
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock factor validation, research-to-review only

## Purpose

Round245 audited the sign of the only notable Round244 clue. Round244 showed `aq_abnormal_accrual_change_reversal` had a negative 5-day raw IC. This round did not treat the sign flip as a free discovery. It preregistered one audit-only factor and counted it as a new hypothesis test:

`aq_abnormal_accrual_change_reversal_sign_flip_audit = -1 * aq_abnormal_accrual_change_reversal`

No portfolio grid, walk-forward, paper, live, or final-holdout action was allowed.

## Implementation

Code changes:

- `src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py`
- `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`

New mode:

`factor_mode=new_substructure_directional_audit`

This mode creates exactly one candidate from the source factor and excludes:

- old raw cash-accrual factors
- repaired cash-accrual factors
- the other Round244 new-substructure factor

## Data And Gates

Report:

`data/reports/round245_accounting_quality_directional_audit_residual_ic_130_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`

Summary:

- Candidate count: 1
- Test count: 2
- Factor rows: 4787
- Aligned rows: 9574
- Multiple-testing lead count: 1
- Neutral gate pass count: 0
- Research lead count: 0
- Promotion allowed candidates: 0

## Results

| Factor | Horizon | IC | ICIR | t-stat | p-value | FDR | Pos IC | Q spread | Industry-neutral IC/t | Size-neutral IC/t | Liquidity-neutral IC/t | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | --- | --- |
| `aq_abnormal_accrual_change_reversal_sign_flip_audit` | 5 | 0.0505 | 0.399 | 2.292 | 0.0219 | true | 66.67% | 0.0082 | 0.1931 / 1.629 | 0.0514 / 2.350 | 0.0519 / 2.275 | false |
| `aq_abnormal_accrual_change_reversal_sign_flip_audit` | 20 | 0.0134 | 0.099 | 0.567 | 0.5706 | false | 54.55% | 0.0086 | 0.0190 / 0.151 | 0.0149 / 0.637 | 0.0164 / 0.668 | false |

## Interpretation

The 5-day sign flip is better than the original direction, but it is not robust enough.

Positive evidence:

- 5-day IC is 0.0505.
- 5-day t-stat is 2.292.
- FDR significant is true after two audit tests.
- Size and liquidity neutral t-stats are above 2.

Blocking evidence:

- Industry-neutral t-stat is only 1.629, below the gate.
- ICIR is 0.399, below the stronger 0.5-0.7 zone expected before serious promotion work.
- 20-day horizon is weak.
- This is a sign audit triggered by a prior result, so the bar must be higher than a first-pass hypothesis.

## Decision

Status: watchlist, not a research lead.

Counts:

- New tested factor: 1
- Useful factors: 0
- Research leads: 0
- Promotable factors: 0
- Walk-forward candidates: 0

Do not run portfolio conversion from this result. Do not continue tuning this sign flip unless a new preregistered industry-neutral repair is defined and counted as another hypothesis.

## Next Direction

Round246 should rotate away from pure accrual-sign work and toward a more event-like accounting family:

- post-statement announcement drift
- profitability revision surprise
- muted reaction after statement improvement

This follows the three-round audit decision: the accounting-quality infrastructure improved, but direct accrual-pressure formulas still have not produced a usable edge.
