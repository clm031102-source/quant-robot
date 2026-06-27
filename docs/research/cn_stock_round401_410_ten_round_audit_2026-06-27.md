# CN Stock Rounds 401-410 Ten-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Summary

Rounds 401-410 improved the 24h sprint shortlist materially.

The block started with Qlib Alpha101 tilt risk repair, rotated to broader public Alpha101/technical projections, fixed an important public-factor source memory problem, and ended with a stronger Alpha101 open-close self-risk observation.

Main outcome:

- Added a stronger high-return risk-budget observation: `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`.
- Added a balanced public-filter observation: `primary_balanced_dragon_hot_chase_alpha101_openclose_top10_cash_zz500075`.
- Kept Qlib self-risk as an important comparator.
- Rejected full-sample traps such as Alpha101/Qlib `m2_cash` variants when OOS pass rate fell to 76.7%.

## Round Summary

| Round | Work | Key Result | Decision |
|---|---|---|---|
| 401 | Qlib tilt self-risk | Qlib drawdown dropped from about -29.8% to -16.1% on stable top10 neg-half | Advance to audit |
| 402 | Qlib self-risk OOS/block/beta | Qlib top10 neg-half passed 90% OOS strict and beta-hedged overlap 0.965 | Add as Qlib risk-budget observation |
| 403 | Qlib ZZ500 multiplier sensitivity | Lower ZZ500 multiplier reduced return; self-risk was better | Stop Qlib multiplier expansion |
| 404 | Public-factor source repair | Fixed memory design; generated 32 public factor target-level values | Use target-level source |
| 405 | Public factor cash/tilt projection | Alpha101 open-close/vwap/intraday were best; sparse Supertrend/Smart-money blocked | Advance to wrapper audit |
| 406 | Alpha101 wrapper/OOS/block/beta | Aggressive tilt: 7.21% ann, -29.84% DD; balanced cash: 6.10% ann, -22.07% DD | Add two simulation observations |
| 407 | Alpha101 self-risk | Self-risk cut Alpha101 tilt drawdown to about -14% to -16% | Audit m2_cash and neg-half |
| 408 | Alpha101 self-risk audit | `m2_cash` failed OOS; `neg_half` passed with 7.52% ann and -16.45% DD | Prefer Alpha101 neg-half |
| 409 | Alpha101 vs Qlib marginal audit | Alpha101 neg-half correlated 0.995 with Qlib but slightly stronger | Add as replacement/variant observation |
| 410 | Ten-round audit and sync | Consolidate evidence and push code/docs/config | Continue after sync |

## Best Candidates After This Block

### Strongest High-Return Risk-Budget Observation

`primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

- full-sample total return: +232.15%
- annualized return: 7.52%
- Sharpe: 1.229
- overlap Sharpe: 0.645
- max drawdown: -16.45%
- OOS mean annualized return: 8.05%
- OOS worst drawdown: -13.44%
- beta-hedged annualized return: 7.49%
- beta-hedged overlap Sharpe: 1.023
- beta-hedged max drawdown: -9.71%

Caveat: correlation to Qlib self-risk is 0.995, so this is not independent new alpha. It is a stronger variant/replacement candidate for simulation.

### Important Comparator

`primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150_self_roll21`

- annualized return: 7.06%
- overlap Sharpe: 0.615
- max drawdown: -16.14%
- OOS mean annualized return: 7.60%
- beta-hedged overlap Sharpe: 0.965

### Balanced Public Filter Observation

`primary_balanced_dragon_hot_chase_alpha101_openclose_top10_cash_zz500075`

- annualized return: 6.10%
- overlap Sharpe: 0.607
- max drawdown: -22.07%
- OOS mean annualized return: 7.10%
- beta-hedged overlap Sharpe: 0.998

This is lower return than the risk-budget candidates but has a clean beta-hedged profile.

## Engineering Output

Implemented and tested a memory-safe public-factor source materialization path:

- narrow each family output before concat;
- target factor values to selected trade date/asset pairs before concat;
- preserve support for Alpha101/Qlib and public technical families.

Tests added to `tests/unit/test_shortlist_public_factor_source.py`:

- `test_family_outputs_are_narrowed_before_cross_family_concat`
- `test_family_outputs_are_targeted_before_cross_family_concat`

## What Failed Or Was Rejected

- Qlib ZZ500 multiplier tuning after self-risk: not better than self-risk.
- Alpha101/Qlib `m2_cash`: strong full-sample result, but OOS strict pass only 76.7%.
- Sparse Supertrend/Smart-money/OBV selected-entry results: high missing share; not promotion evidence.
- Treating Alpha101 open-close as independent from Qlib: return correlation is too high.

## Current Candidate Count

The simulation shortlist config now has 14 candidates. This block added:

- `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150`
- `primary_balanced_dragon_hot_chase_alpha101_openclose_top10_cash_zz500075`
- `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

## Decision

Push this block to GitHub after validation.

Next work should not keep expanding Alpha101/Qlib variants unless the simulation harness needs a final comparison. The next research direction should either:

- prepare same-harness simulation comparison across the best shortlist candidates; or
- rotate to a genuinely independent event/accounting source with sufficient PIT coverage.
