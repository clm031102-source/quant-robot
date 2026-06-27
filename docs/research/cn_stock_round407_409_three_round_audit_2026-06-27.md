# CN Stock Rounds 407-409 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

This block improved the strongest Round406 Alpha101 candidate materially.

The best usable result is `alpha_tilt_open_neghalf`, not the full-sample `m2_cash` winner.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 407 | Applied self-risk overlay suite to Alpha101 Dragon-Hot candidates | Reduced aggressive tilt drawdown from -29.84% to around -14% to -16% | Advance m2_cash and neg_half to audit |
| 408 | OOS/block/beta audit | `m2_cash` failed OOS robustness; `neg_half` survived with 90% strict pass | Prefer `alpha_tilt_open_neghalf` |
| 409 | Marginal comparison versus Qlib self-risk | Alpha101 is highly correlated with Qlib but slightly stronger | Add as replacement/variant observation, not independent alpha |

## Best Usable Result

`alpha_tilt_open_neghalf`

- annualized return: 7.52%
- total return: +232.15%
- overlap Sharpe: 0.645
- max drawdown: -16.45%
- OOS mean annualized return: 8.05%
- OOS worst drawdown: -13.44%
- beta-hedged annualized return: 7.49%
- beta-hedged overlap Sharpe: 1.023
- beta-hedged max drawdown: -9.71%

## Audit Notes

- `m2_cash` is rejected for shortlist despite best full-sample metrics because strict OOS pass is only 76.7%.
- Alpha101 self-risk is not an independent new family; correlation to Qlib self-risk is 0.995.
- The improvement over Qlib is small but measurable, with positive diff t-stat around 2.94.
- This is suitable for simulation comparison, not final promotion.

## Next Direction

Round410 should close the 401-410 ten-round package, update evidence, and sync to GitHub.

After sync, the next mining direction should rotate away from Alpha101/Qlib parameter expansion and focus on simulation harness comparison or genuinely independent event/accounting sources.
