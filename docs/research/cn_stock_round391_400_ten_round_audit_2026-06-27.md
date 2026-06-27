# CN Stock Round391-400 Ten-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Summary

Rounds391-400 changed the public-factor work from broad indicator hunting into selected-entry packaging around the strongest current event lane.

The most useful new result is:

`primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150`

It improves high-return performance versus `dragon_hot_100`, but it is still an aggressive observation rather than a default because Sharpe/overlap are slightly weaker and drawdown is close to 30%.

## Round Decisions

| Block | Direction | Main Result | Decision |
|---|---|---|---|
| 391 | Public ADX on Dragon-Hot | Better drawdown/overlap, source coverage weak | Keep defensive observation only |
| 392 | Self-risk overlays | Roll21 negative-half remains the best risk-budget line | Keep as risk-budget observation |
| 393 | Full-market public factor source | ADX coverage improved but still not clean | Do not promote |
| 394 | Daily-basic filters | PS is defensive; no high-return improvement | Stop broad daily-basic filters |
| 395 | PS + self-risk | Lower drawdown, lower return | Ultra-defensive observation only |
| 396 | PS threshold curve | Smooth defensive trade-off | Stop tuning until projection blocker is repaired |
| 397 | Projection diagnostics | Added unmatched date/year diagnostics | Keep tooling |
| 398 | Qlib Alpha101 on Dragon-Hot | Cash filter failed; exposure tilt worked | Advance top10 x1.5 |
| 399 | Qlib tilt audit | Higher return, capacity clean, risk slightly weaker | Add high-return observation |
| 400 | Ten-round synthesis | Consolidate and sync useful code/docs/config | Push |

## Best Current Lanes

| Lane | Role | Total | Ann. | Sharpe | Overlap | Max DD | Mean OOS Ann. | Worst OOS DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `dragon_hot_100_self_roll21_sum_neg_half` | best risk-budget | 1.9310 | 6.71% | 1.173 | 0.617 | -15.46% | 7.20% | -12.75% |
| `qlib_top10_m150_vt6_zz500_mult_1.00` | aggressive high-return | 1.9015 | 6.65% | 0.969 | 0.522 | -29.79% | 8.38% | -24.98% |
| `dragon_hot_100` | high-return reference | 1.8120 | 6.45% | 0.987 | 0.532 | -28.57% | 8.02% | -23.68% |
| `adx_fullsource_roll42_m3_half` | defensive public-factor observation | 1.8400 | 6.51% | 1.174 | 0.639 | -17.41% | 7.70% | -13.86% |
| `ps_dragon_100_self_roll21_sum_neg_half` | ultra-defensive | 1.5258 | 5.76% | 1.199 | 0.634 | -13.17% | 5.95% | -10.29% |

## What Worked

1. Reusing the Dragon-Hot event lane as the testbed prevented another blind TopN search.
2. Public factor source coverage checks caught the ADX/SuperTrend data-quality issue early.
3. The new tilt tool exposed a useful Qlib signal that cash filters would have wrongly rejected.
4. Projection diagnostics now explain where unmatched contribution comes from instead of just failing with one number.

## What Did Not Work

1. ADX and PS improved risk shape, not high-return performance.
2. Cash-filter framing was too narrow for public Alpha101/Qlib factors.
3. Repeated threshold tuning gave diminishing returns once the family direction was known.
4. The new high-return Qlib tilt is still incremental and correlated with the current Dragon-Hot event lane.

## Process Upgrade

For the next public or event factor family:

1. Start with a long-sample source coverage check.
2. Run both cash-filter and bounded-tilt interpretations when the factor is rank-like.
3. Promote only after wrapper, OOS, block, beta, capacity, and costed-return checks.
4. Stop after one threshold sensitivity curve unless it changes the decision.
5. Rotate family if three rounds do not produce either a high-return observation or a clearly useful risk-budget observation.

## Next Work

1. Test self-risk overlays on `qlib_top10_m150`.
2. Test 0.75/0.50 ZZ500 risk-off variants for the Qlib tilt only if return remains better than `dragon_hot_100`.
3. If the Qlib branch cannot improve risk-adjusted return, rotate to independent accounting/event families rather than continuing Dragon-Hot packaging.

## Sync Decision

Sync code, config, tests, and docs. Do not commit generated `data/reports` artifacts.
