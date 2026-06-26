# CN Stock Rounds101-103 Three-Round Review - 2026-06-22

## Executive Summary

Rounds101-103 completed one full factor-family cycle for capacity-safe public price-volume and low-volatility reversal candidates.

Result:

- New pre-registered candidates: 10
- Long-cycle factor-horizon tests: 20
- Statistical research leads: 1
- Promotable factors: 0
- Dedup verdict: the only lead is highly redundant
- Next direction: rotate away from this exact Bollinger/low-vol reversal cluster

## Round Outcomes

| Round | Purpose | Result | Promotable |
|---:|---|---|---:|
| 101 | Pre-register capacity-safe public price-volume candidates | 10 candidates, 0 blockers | 0 |
| 102 | Long-cycle IC, quantile, turnover, capacity prescreen | 20 tests, 17 FDR-significant, 1 research lead | 0 |
| 103 | Correlation de-duplication for the lead | 3 high-redundancy, 4 moderate-redundancy, 2 unique comparisons | 0 |

## What Was Learned

The family had statistical signal, but not enough independent signal.

The best Round102 lead:

```text
bollinger_reversal_lowvol_liquid_20, horizon 20
```

Round102 metrics:

- IC: 0.0379
- ICIR: 0.314
- t-stat: 16.15
- IC > 0: 61.3%
- Q5-Q1 spread: 0.0184
- quantile monotonicity: 0.800
- top quantile turnover: 24.8%

Round103 then showed that the lead overlaps heavily with existing candidates:

- `donchian_pullback_lowvol_liquid_20`: max abs corr 0.9702
- `rsi_reversal_lowvol_liquid_14_20`: mean abs corr 0.8178
- `range_contraction_lowvol_reversal_20`: max abs corr 0.8568

This means the cycle found a public low-volatility reversal cluster, not a distinct and immediately tradable factor.

## Blocker Histogram

| Blocker | Meaning | Action |
|---|---|---|
| `promotion_requires_later_walk_forward_cost_capacity_regime_gates` | Prescreen cannot prove tradable alpha | Keep hard gate |
| `quantile_monotonicity_weak` | High IC did not translate smoothly across quantiles | Do not tune windows blindly |
| `top_minus_bottom_quantile_not_positive` | Top quantile underperformed bottom quantile | Reject positive long-only direction |
| `lead_highly_redundant_with_existing_candidate` | The only lead is not independent | Rotate family before portfolio grid |
| `drawdown_tolerance_used_as_capacity_waiver` | User drawdown tolerance must not waive capacity | Keep capacity as hard gate |

## Direction Adjustment

Do not run a full Bollinger/RSI/Donchian low-vol reversal portfolio grid now. The lead is too redundant.

Next direction:

```text
round104_family_rotation_after_bollinger_redundancy
```

Round104 should rotate to a factor family with a different return engine, while preserving the same discipline:

- pre-register hypotheses,
- run long-cycle IC/quantile/turnover screen,
- use correlation de-dup before portfolio work,
- treat drawdown below roughly 30% as soft if returns are strong,
- keep capacity, cost, extreme-trade, and execution as hard gates.

## User Risk Tolerance

The user's clarified preference is now part of the process:

- Around 30% drawdown can be acceptable when total return and annualized return are strong.
- Drawdown under that soft tolerance should not be a single-name hard blocker.
- Capacity, tradability, extreme-trade flags, cost, and execution remain hard blockers.

This distinction matters because prior high-return low-turnover results were not blocked only for drawdown; they failed because the returns relied on capacity-constrained names and collapsed after capacity-safe transformations.

## Result

Rounds101-103 did useful research work, but produced no factor worth promotion.

The value of this cycle is negative selection: it prevents the office desktop from spending more compute on a redundant public technical reversal cluster. That is aligned with the goal of building a profitable project rather than an endless factor search.
