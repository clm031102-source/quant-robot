# CN Stock Round397-399 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Summary

This block produced the first new high-return observation after the prior PS/ADX defensive work.

| Round | Direction | Result | Action |
|---|---|---|---|
| 397 | Projection unmatched diagnostic | Added clearer unmatched-date/year diagnostics for selected-entry projections | Keep |
| 398 | Public Alpha101/Qlib on Dragon-Hot | Cash filter failed; exposure tilt worked | Advance `top10 x1.5` |
| 399 | Qlib tilt audit | Higher return, slightly weaker risk shape, capacity clean | Add observation |

## Best New Lane

`primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150`

Formula:

`primary_high_return + Dragon-Hot hot-chase cash filter + 1.50x exposure tilt on selected entries in top 10% of qlib_alpha158_return_std_position_blend_20 + vol_target_6_lb84 + ZZ500 wrapper`

| Metric | Dragon-Hot 100 | Qlib Top10 Tilt |
|---|---:|---:|
| Total return | 1.8120 | 1.9015 |
| Annualized return | 6.45% | 6.65% |
| Sharpe | 0.987 | 0.969 |
| Overlap Sharpe | 0.532 | 0.522 |
| Max drawdown | -28.57% | -29.79% |
| Mean OOS ann. | 8.02% | 8.38% |
| Worst OOS DD | -23.68% | -24.98% |
| ZZ500 hedged ann. | 6.41% | 6.62% |
| ZZ500 hedged DD | -13.28% | -13.72% |

## Method Lesson

The important improvement was not merely another factor name. It was the change in interpretation:

- If a public factor's bad-tail cash filter improves risk while lowering return, it is defensive only.
- If both top and bottom cash filters remove positive contribution, the factor is not an exclusion signal.
- In that case, test a tightly bounded exposure tilt on the profitable side instead of discarding the factor or continuing blind thresholds.

This is a better path than repeating the earlier mistake of forcing every signal family into one cash-filter mold.

## Decision

Add `primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150` to the simulation shortlist config as an aggressive high-return observation.

Do not promote it above the existing Dragon-Hot/self-risk line yet:

- Return improves, but Sharpe and overlap are weaker.
- Drawdown is still close to the user's 30% tolerance.
- The result is incremental and likely highly correlated with the current event lane.

## Next Direction

1. Test self-risk overlays on `qlib_top10_m150` to see whether the added return can survive with lower drawdown.
2. Test a 0.75 ZZ500 risk-off multiplier for the Qlib tilt if return remains competitive.
3. If these do not improve the return/risk trade-off, rotate away from Dragon-Hot packaging to independent event/accounting families.
