# CN Stock Round154-156 Three-Round Review

## Rounds Covered

| Round | Stage | Outcome |
|---:|---|---|
| 154 | Public technical failure-reversal preregistration | 8 candidates across 5 public technical families, 0 portfolio permission |
| 155 | Long-cycle IC/quantile/turnover prescreen | 1 research lead: `inverse_rsrs_slope_failure_liquid_18_60` at 5d |
| 156 | Industry/style neutral and reference de-dup audit | 0 portfolio preflight candidates, 0 promotion |

## What Worked

- The family rotation away from PIT profitability was correct. Round153 had zero controlled IC leads; Round154 moved to public technical failure-reversal hypotheses instead of continuing a dead family.
- Round155 found one raw/industry-plausible signal. Raw IC was 0.0334 with 2,638 observations and a 69.1% positive IC rate.
- Round156 separated raw signal quality from independent alpha. Industry-neutral IC stayed strong at 0.0295, but residual IC fell to 0.0066.

## What Failed

- The lead was not independent. It had 0.9845 mean absolute correlation with `rsrs_slope_inverse_raw_18_60` and 0.9367 with `rsrs_slope_acceleration_quality_18_60`.
- The residual signal was too weak: IC 0.0066, ICIR 0.140, below project gates.
- Residual yearly stability failed in 2018 and 2023.
- No candidate earned permission for a portfolio grid, promotion, or manual/live use.

## Direction Audit

This was not the same mistake as the earlier moneyflow lock-in. The process rotated family after the PIT profitability line failed and tested public technical ideas. The Round156 failure says something specific: this RSRS branch is too redundant and weak after neutralization.

The next mistake to avoid is RSRS parameter grinding. More RSRS windows or TopN grids would be a lower-quality search because the blocker is structural redundancy, not an untested parameter.

## Decision

- Promote: 0.
- Portfolio preflight: 0.
- Research leads retained: 0 active from this cluster.
- Hibernated direction: public RSRS inverse/failure-reversal cluster.
- Next direction: `round157_rotate_after_public_technical_failure_reversal_neutral_dedup_failure`.

Round157 should start a different family with a different economic mechanism. Preferred options are event-aware price-volume reversal, earnings/announcement drift with strict PIT, or a public non-RSRS technical family with explicit industry/style neutralization from the first screen.
