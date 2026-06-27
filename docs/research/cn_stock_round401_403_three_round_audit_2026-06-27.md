# CN Stock Round401-403 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Summary

The Qlib top10 tilt became materially more useful after applying the existing self-risk framework.

| Round | Direction | Result | Decision |
|---|---|---|---|
| 401 | Qlib tilt self-risk suite | Self-risk improved return/risk sharply | Audit best candidates |
| 402 | OOS/block/beta audit | Top10 neg-half stable; top15 m2 cash overfit risk | Add top10 neg-half observation |
| 403 | ZZ500 multiplier sensitivity | Defensive risk-off variants lowered return too much | Do not add separate lane |

## Best Candidate

`primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150_self_roll21`

| Metric | Dragon-Hot Self-Risk | Qlib Top10 Tilt Self-Risk |
|---|---:|---:|
| Total return | 1.9310 | 2.0917 |
| Annualized return | 6.71% | 7.06% |
| Sharpe | 1.173 | 1.174 |
| Overlap Sharpe | 0.617 | 0.615 |
| Max drawdown | -15.46% | -16.14% |
| Mean OOS ann. | 7.20% | 7.60% |
| Worst OOS DD | -12.75% | -13.48% |
| ZZ500 hedged ann. | 6.68% | 7.02% |
| ZZ500 hedged DD | -9.49% | -10.14% |

## Audit Judgment

This is currently the best new observation from the Qlib branch.

It is not promoted as default yet because:

- it is still built on the same low-turnover/Dragon-Hot event stack;
- the improvement is incremental, not orthogonal;
- overlap Sharpe is not higher than Dragon-Hot self-risk;
- final 2026 holdout remains sealed.

It is worth carrying into simulation because:

- it improves full-sample and OOS annualized return versus Dragon-Hot self-risk;
- drawdown remains far below the user's 30% tolerance;
- beta and capacity diagnostics remain acceptable;
- it emerged from a public, reproducible factor source rather than another blind moneyflow parameter sweep.

## Next Direction

Stop expanding Qlib parameters for now.

Next work should rotate to a genuinely independent source family, preferably:

1. accounting/event timeliness with clean point-in-time lag handling;
2. analyst/report revision if a reliable cache can be built;
3. industry-relative event surprise or earnings-quality drift;
4. only return to Qlib if the simulation phase needs one more aggressive risk-budget comparison.
