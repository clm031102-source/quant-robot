# CN Stock Round160-162 Three-Round Review

Date: 2026-06-23

## Scope

This review satisfies the governance rule: every 3 rounds, audit the previous work and adjust the plan before continuing factor mining.

Reviewed rounds:

- Round160: tradeability/limit-event proxy prescreen
- Round161: family rotation decision and market-regime-temperature preregistration
- Round162: market-regime-temperature residual prescreen

## Outcomes

| Round | Work | Unique candidates | Useful leads | Portfolio candidates | Promotion candidates | Decision |
|---:|---|---:|---:|---:|---:|---|
| 160 | Tradeability/limit-event proxy prescreen | 8 | 0 | 0 | 0 | Failed; do not audit true-limit feed or run portfolio grids |
| 161 | Family rotation + preregistration | 6 | prereg only | 0 | 0 | Correct process; selected a non-recent-failed mechanism |
| 162 | Market-regime-temperature residual prescreen | 6 | 0 | 0 | 0 | Failed strict residual lead gate |

## What Improved

The process improved in three concrete ways:

- The startup gate now absorbs Round160 failure and prevents reentering tradeability/limit-event parameter tuning.
- A reusable family-rotation decision tool now reviews recent failed families before selecting the next direction.
- Round161/Round162 enforced lagged regime state, residual evaluation, state coverage, no same-day leakage, no portfolio grid before prescreen, and no promotion.

## Why The New Family Still Failed

The selected regime-temperature family was directionally better than blind factor search, but the strongest signals were not clean enough.

`regime_cold_liquidity_reversal_quality_20_5`:

- Residual IC: 0.0289
- Residual ICIR: 0.328
- Positive IC rate: 60.0%
- Failure: 2024 residual IC turned slightly negative
- Main exposure problem: correlation to `return_20` was -0.9365

This means the signal is mainly a regime-conditioned reversal exposure. It may be informative, but it is not a clean standalone factor yet.

`index_location_low_residual_value_liquidity_60_10`:

- Residual IC: 0.0254
- Residual ICIR: 0.217
- Positive IC rate: 56.4%
- Failure: industry-neutral IC is too weak, and liquidity exposure is high

This is also not clean enough for portfolio conversion.

## Stop-Loss Decision

Do not continue this family by simple parameter tuning.

Blocked next actions:

- regime-temperature portfolio grid before a new residual lead;
- promoting `regime_cold_liquidity_reversal_quality_20_5` from IC only;
- widening thresholds because the user can accept drawdown;
- same-day or unlagged market-temperature state;
- reusing external macro/northbound/credit feeds before a local data audit proves coverage.

## Adjusted Plan

Round163 should rotate again unless a new pre-registered decomposition is created for the cold-liquidity observation.

Preferred next action:

- `round163_rotate_after_china_market_regime_temperature_residual_prescreen_failure`

Permitted diagnostic branch:

- a separate decomposition audit of cold-liquidity reversal that removes `return_20` exposure and stress-tests 2024 before any portfolio work.

Portfolio and promotion remain blocked.

