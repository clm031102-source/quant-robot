# CN Stock Round256-258 Three-Round Review

- Date: 2026-06-26
- Scope: CN A-share stock factor mining
- Review cadence: every 3 factor-mining rounds
- Covered rounds: 256, 257, 258
- Final holdout: still blocked from tuning

## Round Summary

| Round | Direction | Candidates | Tests | Research Leads | Promotion | Decision |
|---:|---|---:|---:|---:|---:|---|
| 256 | forecast guidance uncertainty | 3 | 6 | 0 | 0 | hibernate forecast guidance line |
| 257 | frozen daily-basic full-sample replay | 10 | 20 | 0 | 0 | one diagnostic valuation line only |
| 258 | valuation coverage repair and exposure audit | 2 gate candidates, 1 repaired prescreen candidate | 2 repaired prescreen tests + exposure audit | 0 | 0 | hibernate daily-basic valuation repair line |

## What Improved

The workflow improved materially versus earlier blind mining:

- short-window evidence was not trusted;
- old parameters were replayed unchanged over 2015-2025;
- candidate plans were gated before factor generation;
- FDR-significant IC was treated as insufficient without quantile shape and exposure survival;
- coverage repair was justified before any portfolio evidence;
- L-only stock-basic industry metadata was cross-checked with L+D all-status metadata.

## What Failed

The strongest apparent result in this window was not real enough:

`daily_basic_valuation_reversion_dvratio_quality_60`

- h20 raw IC: 0.0661
- h20 ICIR: 0.533
- h20 t-stat: 27.44
- h20 IC>0: 69.8%
- h20 Q5-Q1: 0.0137
- h20 monotonicity: 0.40
- residual IC after industry/style controls: 0.0151
- residual retention: 22.9%
- max style correlation: 0.9479

This is not a clean alpha. It is mostly a valuation/style exposure with weak long-only quantile translation.

## Reject Reason Histogram

- zero research leads after PIT/full-sample controls: 3 rounds
- coverage blocker repaired but not promoted: 1 family
- quantile shape failure: daily-basic valuation repair and multiple Round257 daily-basic candidates
- style exposure dominance: daily-basic valuation repair
- raw IC/FDR not enough for promotion: repeated

## Direction Adjustment

Round259 must rotate away from:

- forecast guidance or old forecast surprise formulas;
- standalone daily-basic valuation repair;
- daily-basic direction flips or parameter sweeps;
- public reference direct grids that already failed quantile shape;
- moneyflow/main-force direct grids that failed low ICIR or quantile gates.

Allowed next direction:

`round259_rotate_after_daily_basic_valuation_repair_failure_to_new_orthogonal_non_daily_basic_family`

The next family should be non-daily-basic and non-forecast, and must enter with the following controls from the first screen:

- same-parameter full-cycle replay or full-cycle prescreen;
- industry/style residual IC;
- quantile shape gate;
- coverage and capacity gate;
- no 2026 tuning;
- no portfolio grid before residual evidence.

## Budget-Waste Stop Loss

Stop-loss decision: daily-basic valuation repair is hibernated as a direct line. It can only re-enter with a new orthogonal economic hypothesis, not by changing weights, replacing more fields, sign flipping, or lowering thresholds.

## Current Best Evidence

No factor from rounds 256-258 is promotable.

One useful engineering/method result did emerge: full-sample, same-parameter replay prevents a strong raw IC from being mistaken for a tradable factor. The Round258 failure is productive because it saved budget before portfolio-grid overfitting.
