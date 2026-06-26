# CN Stock Daily-Basic Free-Float Supply Quality Residual Stability Audit Round134

Date: 2026-06-22

## Scope

- Machine role: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Stage: `daily_basic_free_float_supply_quality_residual_stability_audit`
- Lead: `daily_basic_free_float_supply_quality_20`, horizon 20
- Input audit: `docs/research/cn_stock_daily_basic_non_price_public_carry_lead_dedup_round133_2026-06-22.md`
- Output pack: `data/reports/daily_basic_free_float_supply_quality_residual_stability_audit_round134_20260622`
- Final holdout: not included

Round134 answers the Round133 blocker: whether the 2023 implementation-residual IC failure was an unexplained regime break or a controllable data/regime condition.

## Data Window

| Item | Value |
|---|---:|
| Bar rows | 10,785,537 |
| Bar assets | 5,707 |
| Bar date range | 2015-01-05 to 2025-12-31 |
| Daily-basic rows | 3,262,000 |
| Daily-basic assets | 5,567 |
| Daily-basic date range | 2023-07-03 to 2025-12-31 |
| Lead factor rows | 3,262,000 |
| Residual rows | 2,238,870 |
| Strict-clean factor rows | 3,128,522 |
| Strict-clean residual rows | 2,169,592 |
| Label rows | 10,665,909 |

The long-cycle bar authority starts in 2015, but this family is limited by available Tushare daily-basic inputs from 2023-07-03 onward. The run still uses all available daily-basic dates through 2025-12-31 and excludes 2026 final holdout.

## Round134 Result

| Metric | Raw lead | Implementation-residual lead | Strict-clean residual lead |
|---|---:|---:|---:|
| IC observations | 586 | 586 | 586 |
| Mean IC | 0.039225 | 0.034488 | 0.036081 |
| ICIR | 0.311307 | 0.525926 | 0.554635 |
| t-stat | 7.535934 | 12.731320 | 13.426284 |
| IC positive rate | 63.48% | 74.91% | 75.77% |
| Median cross-section | 5,349 | 3,722 | 3,509.5 |

Strict-clean filtering did not weaken the signal. It slightly improved residual mean IC and ICIR, which argues against the lead being just a dirty-field or illiquid-row artifact.

## Stability Diagnosis

Residual failed months:

| Month | Obs | Residual mean IC | IC+ | Dominant state | Note |
|---|---:|---:|---:|---|---|
| 2023-07 | 21 | -0.058735 | 38.10% | stress, weak breadth, high vol | coverage-onset month |
| 2023-08 | 23 | -0.015280 | 47.83% | stress, weak breadth, low vol | coverage-onset month |
| 2023-11 | 22 | -0.011306 | 18.18% | stress, weak breadth, normal vol | post-onset stress |
| 2023-12 | 21 | -0.045870 | 23.81% | stress, weak breadth, low vol | post-onset stress |
| 2024-02 | 15 | -0.000672 | 40.00% | stress, strong breadth, high vol | post-onset stress |
| 2025-04 | 21 | -0.014828 | 38.10% | stress, strong breadth, high vol | post-onset stress |

Coverage-onset split:

| Phase | Obs | Mean IC | ICIR | IC+ | Failure |
|---|---:|---:|---:|---:|---|
| Coverage onset | 63 | -0.015194 | -0.186 | 55.56% | true |
| Post onset | 523 | 0.040472 | 0.666 | 77.25% | false |

Interpretation:

- The weak months are explainable but not ignorable. All six failed months are stress-regime months; none are dominant non-stress months.
- The first two failed months are also the daily-basic coverage onset period.
- The post-onset aggregate is strong: mean IC 0.040472, ICIR 0.666, IC+ 77.25%.
- Raw-vs-residual sensitivity exists: three failed residual months did not fail in raw IC, so neutralization changes behavior in stress windows.

## Decision

- Promotion allowed: `false`
- Portfolio grid allowed before review: `false`
- Gate blockers: none after attributing failures to coverage-onset or stress state
- Gate observations:
  - `coverage_onset_or_stress_only_residual_failure`
  - `raw_pass_residual_fail_neutralization_sensitivity`
- Stability repair candidate: `true`
- Next direction: `round135_round132_134_three_round_review_before_next_action`
- Recommended post-review direction: `round135_daily_basic_free_float_supply_quality_strict_clean_portfolio_preflight_after_review`

This is the first daily-basic candidate in the recent chain that remains interesting after coverage, capacity, de-duplication, implementation-neutralization, and strict-clean residual checks. It is still not paper-ready or promotable because no costed portfolio, walk-forward fold acceptance, stress-regime guard, capacity participation, or final holdout validation has been run.

## Three-Round Context

| Round | Direction | Main Evidence | Decision |
|---|---|---|---|
| 132 | Daily-basic non-price public carry prescreen | 10 candidates, 20 tests, 3 coverage-pass candidates, 1 research lead, 0 promoted | Advance only the clean lead to de-dup |
| 133 | Lead de-dup and implementation residual | No high redundant reference factor; 0 high implementation exposures; residual mean IC 0.034488, ICIR 0.525926 | Block direct conversion due residual yearly instability |
| 134 | Residual stability audit | Strict-clean residual mean IC 0.036081, ICIR 0.554635; failures explainable by coverage-onset or stress state | Require three-round review, then strict-clean regime-aware preflight |

## Bright Data

- Round132 found one clean research lead with mean IC 0.039225, t-stat 7.54, Q5-Q1 spread 0.5015, quantile monotonicity 0.900, top-quantile turnover 0.91%, field coverage clean ratio 99.39%, and capacity clean ratio 96.45%.
- Round133 showed the lead survived implementation-neutralization: residual ICIR improved from 0.311307 to 0.525926 and IC positive rate improved from 63.48% to 74.91%.
- Round134 showed strict-clean masking did not kill the signal: strict-clean residual ICIR improved again to 0.554635 and IC positive rate reached 75.77%.
- The post-onset residual sample is materially stronger than the onset sample: 523 observations, mean IC 0.040472, ICIR 0.666, IC+ 77.25%.

## Limits

- Daily-basic history only starts at 2023-07-03, so this factor family still lacks a 2015-2022 daily-basic factor replay.
- This is IC evidence, not costed profitability evidence.
- Stress-regime weakness must be handled before any return-maximizing top-N sweep.
- A 30% drawdown tolerance can be used later in risk settings, but it does not waive capacity, stress stability, cost, or walk-forward gates.

## Required Round135 Review

Round135 must be a three-round review for Rounds132-134 before new factor mining or portfolio-grid work. It should decide whether to run the recommended strict-clean regime-aware preflight or rotate away.

Minimum review checks:

1. Confirm no portfolio promotion claim is being made from Round132-134.
2. Confirm `daily_basic_free_float_supply_quality_20` is a research lead, not a tradable signal yet.
3. If continuing, pre-register a strict-clean portfolio preflight with a stress-state guard and no parameter expansion.
4. If rejecting, hibernate the share-structure daily-basic line and rotate to a new nonredundant family.

## Safety

This is research-to-review only. No broker connection, no account reads, no order placement, and no live trading.
