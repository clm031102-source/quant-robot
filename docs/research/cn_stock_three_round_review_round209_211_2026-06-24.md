# CN Stock Three-Round Review Round209-211 - 2026-06-24

## Executive Summary

Rounds 209-211 followed the new three-round review rule and produced no promotable factor.

The work was still useful because it converted two recurring failure modes into reusable gates:

- tradeability structure is now a hard risk/control layer, not a standalone alpha family;
- strong daily-basic valuation IC with weak field coverage must go through repair audit and fresh prescreen before reuse.

The only candidate worth further work is not promotable:

```text
daily_basic_valuation_reversion_dvratio_quality_60
```

It has strong h20 IC after coverage repair, but its quantile shape is too weak for a strict research lead.

## Round Outcomes

| Round | Direction | Main Evidence | Decision |
|---:|---|---|---|
| 209 | Tradeability structure quality | 4 candidates, 8 tests, 7 FDR-significant rows, all mean IC non-positive | no alpha; keep as hard execution/survivorship control |
| 210 | Daily-basic valuation coverage audit | 2 valuation targets; 1 repair-ready, 1 blocked; `dv_ratio` passed replacement coverage for `dv_ttm` | allow only repaired valuation reversion preregistration |
| 211 | Coverage-repaired valuation reversion prescreen | h20 IC 0.0677, ICIR 0.526, IC>0 67.2%, coverage clean 92.3%, but monotonicity 0.400 | diagnostic lead only; no portfolio grid |

## What Worked

- The process rotated away from the failed 52-week and tradeability-alpha directions.
- Round210 prevented a false binary decision on Round132: the old valuation factor was neither usable nor fully dead.
- The `dv_ratio` replacement fixed the daily-basic coverage blocker.
- CLI support for custom daily-basic candidate spec JSON now makes repair-only reruns reproducible.
- The startup gate now records that coverage repairs must be preregistered and rescreened.

## What Failed

- Round209 showed tradeability structure is not a clean higher-is-better alpha signal.
- Round211 did not produce a strict research lead because the repaired valuation factor failed quantile monotonicity.
- The h5 version has negative Q5-Q1, so the short-horizon payoff shape is unreliable.
- No factor passed portfolio, paper, promotion, cost/capacity, regime, or walk-forward gates.

## Bright Data

The most promising numeric result in these rounds is Round211 h20:

- Factor: `daily_basic_valuation_reversion_dvratio_quality_60`
- Horizon: 20
- Mean Spearman IC: 0.0677
- ICIR: 0.526
- t-stat: 12.72
- IC positive rate: 67.2%
- FDR-significant: yes
- Required-field clean ratio: 92.3%
- Capacity clean ratio: 95.9%

This is worth investigation, but not promotion. The blocker is shape translation: Q5-Q1 is only 2.54% and monotonicity is 0.400.

## Direction Adjustment

Immediate next step:

```text
round212_daily_basic_valuation_reversion_shape_exposure_audit
```

Round212 should answer:

- Is the strong IC mostly industry/style/value beta?
- Does residualization preserve IC?
- Which quantile buckets break monotonicity?
- Is the signal useful as bottom-exclusion or middle-bucket avoidance rather than top-long ranking?
- Is the payoff concentrated in microcap/capacity tails?
- Does the h20 shape survive monthly/yearly slices?

Round212 must not:

- run TopN grids;
- tune weights or windows;
- call the h20 IC a tradable factor;
- read final holdout;
- promote any result before exposure, shape, cost/capacity, regime, and walk-forward gates.

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Strict research leads: 0
- Diagnostic leads for further audit: 1
- New reusable gates/tools: 2
- Next family status: continue only with shape/exposure audit of the repaired valuation signal; rotate away if residual or shape audit fails
