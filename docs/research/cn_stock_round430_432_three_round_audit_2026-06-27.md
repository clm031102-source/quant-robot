# CN Stock Round430-432 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

This audit reviews the execution-risk repair work after Round428 downgraded the Round425 default to conditional because extreme realized trades contributed too much of total return.

The three-round objective was not to mine more weak variants. It was to answer whether the best candidate can survive a cleaner execution treatment before any simulation handoff.

## Round Summary

| Round | Work | Decision |
|---:|---|---|
| 430 | Added trade-level cohort rows and an extreme-trade profile tool. Tested `roundtrip_cash_proxy_weighted_return` repairs. | `roundtrip_m150` is useful as execution-stress research, but not clean because it uses exit-date tradeability evidence. |
| 431 | Tested entry-known public-tilt risk caps using `turnover_rate_f` and `pb`. | Rejected. Caps slightly reduce drawdown/extreme contribution but trail the uncapped candidate on return, OOS overlap, and beta-hedged return. |
| 432 | Built causal delayed-exit return repair for unsellable planned exits, preserving zero-return event dates. | `round432_delayed_exit_m150` becomes the current best research-to-paper candidate, pending heavy-cost stress and replay/handoff gates. |

## Best Candidate After The Audit

Candidate:

`round432_delayed_exit_m150`

Key metrics:

| Metric | Value |
|---|---:|
| annualized return | 6.663% |
| total return | +218.46% |
| Sharpe | 0.968 |
| overlap Sharpe | 0.496 |
| max drawdown | -26.21% |
| win rate | 41.33% |
| mean OOS annualized return | 10.043% |
| mean OOS overlap Sharpe | 0.831 |
| worst OOS drawdown | -19.30% |
| OOS strict pass | 90.00% |
| beta-hedged annualized return | 7.485% |
| beta-hedged overlap Sharpe | 0.792 |
| beta-hedged max drawdown | -14.14% |
| alpha t-stat | 4.36 |
| leave-one-year min annualized return | 5.00% |
| leave-one-year min overlap Sharpe | 0.425 |
| best three months log share | 45.72% |

## Risk Findings

1. The old Round425 default remains useful but conditional, not clean.

The Round428 warning still matters: the default's ordinary full-sample/OOS metrics were acceptable, but the extreme-trade dependency was too high for an unaudited simulation handoff.

2. Round430's `roundtrip_m150` was a diagnostic bridge, not a final factor.

It improved drawdown and overlap metrics, but it used exit-date tradeability evidence. That is acceptable for stress diagnostics, not for a paper-simulation entry rule.

3. Round431 threshold caps were not worth the complexity.

The caps added parameters but did not materially reduce the extreme tail. They are a classic overfitting risk: small metric polish, weak economic improvement.

4. Round432 is stronger because it repairs execution mechanics rather than selecting away realized winners.

The delayed-exit repair is closer to a real trading process: if a planned exit cannot be sold, delay until the first sellable date within the window. It also preserves zero-return events so performance is not inflated by dropped rows.

## Decision

Promote `round432_delayed_exit_m150` to current best research-to-paper candidate.

Do not mark it paper-ready yet.

Required before paper-simulation handoff:

- run 20 bps and 30 bps delayed-exit cost stress;
- replay the candidate through the simulation shortlist handoff gate;
- compare it against the existing Round424/425 10/20/30 bps lanes;
- keep 2026 final holdout sealed until final validation is explicitly started;
- record whether the remaining extreme contribution is acceptable or needs an entry-known capacity/risk budget.

## Direction For Next Work

Next round should be a cost and replay gate for the delayed-exit candidate, not a new factor family.

If delayed-exit fails heavy-cost stress, rotate away from micro-threshold tuning. The next useful families are:

- capacity-aware execution rules;
- market-regime and index-position overlays;
- PIT accounting quality after announcement-date lag checks;
- industry/size/value/liquidity neutralized versions;
- independent public technical families only when they beat the current delayed-exit baseline after costs.
