# CN Stock Round110-112 Three-Round Review - 2026-06-22

## Scope

This review closes the governed three-round block:

- Round110: market residual risk-premia preregistration.
- Round111: market residual IC/quantile/turnover prescreen.
- Round112: lead exposure, yearly stability, and reference-correlation dedup audit.

Market/asset stayed CN stock. Final 2026 holdout was not used.

## What Worked

The process improved materially versus blind parameter sweeping.

| Round | Purpose | Candidates / Tests | Best Evidence | Promotion |
|---:|---|---:|---|---:|
| 110 | Preregister residual risk-premia candidates | 10 candidates | Changed source family after Round107-109 failures; required signal-date equal-weight market proxy | 0 |
| 111 | Alphalens-style prescreen | 10 candidates, 20 tests | `beta_adjusted_range_contraction_60` 20d IC 0.0559, ICIR 0.371, t 18.89, IC+ 67.13%, monotonicity 1.0 | 0 |
| 112 | Lead dedup/exposure/stability audit | 1 lead, 4 references, 5 exposures | 9,843,366 lead rows; 40,479,172 reference rows; Donchian branch high redundancy; 3 high exposures; 2015 failure confirmed | 0 |

Bright data:

- Round111 found the first clean statistical lead after several zero-lead families.
- The lead had strong IC-level evidence: mean IC 0.0559 and t-stat 18.89 over 2,592 dates.
- The pipeline caught the problem before a portfolio grid: Round112 showed the lead was not clean enough.

## What Failed

The lead did not survive promotion gates.

Reject reason histogram:

| Reason | Count / Evidence | Meaning |
|---|---:|---|
| Not a research lead in prescreen | 9 candidates | Statistically significant rows existed, but most failed ICIR/lead quality gates. |
| High reference redundancy | 1 lead blocker | `donchian_pullback_lowvol_liquid_20` max abs corr 0.9768 with the lead. |
| Moderate reference redundancy | 1 warning | `range_contraction_lowvol_reversal_20` mean abs corr 0.4932, max abs corr 0.8304. |
| High exposure dependence | 3 diagnostics | Residual vol, market corr, and episodic liquidity exposure blocked standalone alpha use. |
| 2015 regime failure | 1 year | 2015 mean IC -0.1021, IC+ 23.78%. |
| Monthly instability | 38 of 129 months | Failure months clustered strongly in 2015 and appeared elsewhere. |
| Paper-ready candidates | 0 | No cost/capacity/walk-forward bridge is allowed. |

## Interpretation

`beta_adjusted_range_contraction_60` is not useless. It is a real statistical signal, but the evidence says it is closer to a low-residual-volatility/range-pullback risk-premia component than a standalone tradable alpha.

The user risk preference matters: a 30% drawdown is not automatically disqualifying. But Round112 blockers are not drawdown blockers. They are signal-cleanliness blockers:

- redundancy with an existing public-style Donchian/range branch;
- strong residual-volatility and market-correlation exposure;
- confirmed 2015 regime failure;
- no cost/capacity/walk-forward portfolio evidence.

## Direction Adjustment

Do not continue the market-residual lead as a standalone TopN strategy.

Hibernated directions:

- market residual portfolio grid after Round112 blockers;
- beta-adjusted range contraction bridge before three-round review;
- Donchian-redundant continuation;
- treating residual-volatility exposure as alpha without neutralization.

Carry-forward value:

- The equal-weight market proxy and rolling residual feature machinery are useful infrastructure.
- The lead can be reused later as a risk-control or neutralization test input, not as a promoted factor.
- The exposure-dedup audit should remain mandatory before any future TopN grid.

## Public Method Review

The next family should use a public-reference translation layer rather than inventing another ad hoc formula family.

Recommended source:

- WorldQuant 101 Alpha style formulas, translated conservatively into CN stock capacity-safe, signal-date-only expressions.

Constraints:

- Pre-register formulas before evaluation.
- Use 2015-2025 long-cycle data.
- Exclude 2026 holdout.
- Keep `min_signal_date_amount` and capacity filters.
- Run Alphalens-style IC/ICIR/quantile/turnover prescreen before any portfolio grid.
- Deduplicate against existing price-volume, Donchian/range, low-vol, and market-residual clusters.
- Apply cumulative multiple-testing accounting.

## Decision

Round110-112 produced 10 preregistered candidates, 20 prescreen tests, 1 statistical research lead, and 0 promotable factors.

The market-residual standalone line is hibernated after Round112. The next direction is:

`round114_public_alpha101_capacity_safe_preregistration`

Round114 should preregister a small, curated public Alpha101-style candidate set, not run a broad random formula search.
