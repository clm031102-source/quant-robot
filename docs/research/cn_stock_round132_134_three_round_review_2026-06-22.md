# CN Stock Round132-134 Three-Round Review - 2026-06-22

## Scope

This review covers the daily-basic non-price public-carry line after the Round129-131 review:

- Round132: daily-basic non-price public-carry prescreen.
- Round133: `daily_basic_free_float_supply_quality_20` de-duplication and implementation-residual audit.
- Round134: residual stability audit by coverage-onset, market state, and strict-clean mask.

This review is required before any new factor mining, parameter expansion, or portfolio-grid work.

## Decision

Decision: continue only as a constrained strict-clean, stress-guard portfolio-conversion preflight.

Next direction:

`round136_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_after_review`

Promotion remains blocked. The candidate is a research lead, not a paper-ready or live signal.

## Evidence Summary

| Round | Candidates / Tests | Main Result | Promotion |
|---|---:|---|---:|
| 132 | 10 candidates, 20 factor-horizon tests | 1 research lead after coverage, capacity, IC, spread, monotonicity, and multiple-testing checks | 0 |
| 133 | 1 lead, 9 daily-basic references | 0 high redundant references, 0 high implementation exposures, residual IC survived neutralization | 0 |
| 134 | 1 residual lead under state and strict-clean audit | Strict-clean residual improved ICIR; weak months were coverage-onset or stress-regime months | 0 |

## Best Research Lead

`daily_basic_free_float_supply_quality_20`, horizon 20:

| Metric | Round132 raw | Round133 residual | Round134 strict-clean residual |
|---|---:|---:|---:|
| IC observations | 586 | 586 | 586 |
| Mean IC | 0.039225 | 0.034488 | 0.036081 |
| ICIR | 0.311307 | 0.525926 | 0.554635 |
| t-stat | 7.535934 | 12.731320 | 13.426284 |
| IC positive rate | 63.48% | 74.91% | 75.77% |
| Median cross-section | 5,349 | 3,722 | 3,509.5 |

Why it remains interesting:

- It passed Round132 field coverage and capacity cleanliness: field coverage clean ratio 99.39%, capacity clean ratio 96.45%.
- It passed Round132 economic structure checks: Q5-Q1 spread 0.5015, quantile monotonicity 0.900, top-quantile turnover 0.91%.
- Round133 found no high redundant daily-basic reference factor and no high implementation exposure.
- Round134 showed strict-clean masking did not kill the residual signal; ICIR rose from 0.525926 to 0.554635.
- Post-onset residual IC is materially stronger than the onset period: 523 observations, mean IC 0.040472, ICIR 0.666, IC+ 77.25%.

## Why It Is Still Not Promotable

The result is not a verified profitable factor yet.

Hard limits:

- The daily-basic input history starts at 2023-07-03, so this family does not have 2015-2022 daily-basic factor evidence.
- Evidence so far is IC, quantile, redundancy, residual, and stability evidence; it is not a costed portfolio return path.
- Six residual failed months exist: 2023-07, 2023-08, 2023-11, 2023-12, 2024-02, 2025-04.
- All failed residual months are stress-regime months, so a stress guard is required before any return-maximizing TopN sweep.
- Raw-vs-residual sensitivity remains: three failed residual months did not fail in raw IC, which means neutralization changes stress behavior.
- No walk-forward accepted folds, capacity participation simulation, transaction-cost stress, drawdown path, or final holdout has been run.

The user's 30% drawdown tolerance changes the later risk-acceptance threshold, but it does not waive costs, capacity, stress-regime robustness, data cleanliness, or walk-forward validation.

## Rejected Paths

Do not do these next:

- Direct TopN portfolio grid from Round132/133/134 IC.
- More daily-basic share-structure parameter expansion before portfolio conversion.
- Reusing `daily_basic_valuation_reversion_quality_60` before repairing its field-coverage clean ratio.
- Inverting failed daily-basic candidates without new preregistration.
- Treating stress-regime filtering as a post-hoc return optimizer.
- Reading 2026 final holdout before an OOS and walk-forward clearance path exists.

## Required Round136 Preflight

Round136 may proceed only as a single-candidate conversion preflight with frozen factor definition:

`daily_basic_free_float_supply_quality_20`

Required design:

1. Use the strict-clean factor/residual mask: field coverage ratio >= 0.95, amount and ADV20 amount >= 10,000,000.
2. Use the same horizon: 20 trading days.
3. Use the same implementation residual exposures: `log_circ_mv`, `log_total_mv`, `inv_pb`, `dv_ttm`, `log_adv20_amount`.
4. Add a pre-registered stress-state guard based only on signal-date market state.
5. Compare guarded and unguarded paths, but do not tune guard thresholds from return results.
6. Include realistic costs, turnover, holding-overlap adjustment, trade count, max drawdown, Sharpe, annualized return, win rate, and capacity participation.
7. Require walk-forward fold evidence before any paper-ready claim.
8. Keep 2026 excluded as final holdout.

## Stop-Loss Rule

If Round136 cannot convert the strict-clean residual lead into a costed and capacity-aware portfolio path with acceptable walk-forward evidence, hibernate the daily-basic share-structure line and rotate to a new nonredundant public-reference family.

Do not spend another round expanding windows or filters in this same family unless Round136 shows a concrete IC-to-portfolio translation failure that a pre-registered bridge can plausibly solve.

## Count

| Category | Count |
|---|---:|
| New Round132 preregistered/evaluated candidates | 10 |
| New Round132 research leads | 1 |
| New Round133/Round134 factor formulas | 0 |
| Promotable factors from Rounds132-134 | 0 |
| Paper-ready factors from Rounds132-134 | 0 |
| Manual/live usable factors | 0 |
| Continue candidates after review | 1 |

## Safety

This remains research-to-review only. No broker connection, no account reads, no order placement, and no live trading.
