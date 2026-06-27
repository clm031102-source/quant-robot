# CN Stock Round394-396 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Rounds

| Round | Direction | Result | Decision |
|---:|---|---|---|
| 394 | Daily-basic selected-entry filters on Dragon-Hot | PS is the only useful defensive filter; no high-return improvement | advance PS only |
| 395 | PS-on-Dragon plus self-risk | `ps_dragon_100_self_roll21_sum_neg_half` is a credible ultra-defensive observation | add observation only |
| 396 | PS threshold sensitivity | smooth risk-return curve; no single-parameter artifact | stop PS tuning until projection blocker is fixed |

## Key Findings

This three-round block did not discover a new high-return alpha factor.

It did produce a useful low-drawdown simulation profile:

`primary_high_return_dragon_hot_chase_ps20_self_risk_roll21`

Metrics:

- full-sample total return: 152.58%;
- annualized return: 5.76%;
- Sharpe: 1.199;
- overlap-adjusted Sharpe: 0.634;
- max drawdown: -13.17%;
- mean OOS annualized return: 5.95%;
- worst OOS drawdown: -10.29%;
- OOS strict pass rate: 90%;
- CSI500 beta: 0.0275;
- CSI500 hedged annualized return: 5.72%;
- CSI500 hedged overlap: 0.999;
- CSI500 hedged max drawdown: -7.78%.

## Audit Judgment

Useful but not promotable.

The PS filter is a defensive risk-control layer. It should not be represented as a standalone profitable factor or a replacement for the current high-return Dragon-Hot/self-risk lane.

The family has one unresolved blocker:

- Round394 PS projection unmatched absolute contribution was 0.0120 versus the 0.005 limit.

This must be fixed before any promotion claim. The acceptable use today is simulation observation only.

## Process Update

The correct use of public value/valuation fields in this project is not direct TopN mining. Round352 already rejected direct daily-basic public-anomaly portfolios. The useful mode is selected-entry filtering inside a stronger trading surface.

Next direction:

- repair official-template projection tolerance/calendar handling for selected-entry secondary filters;
- continue searching for independent sources rather than tuning PS further;
- keep high-return and low-drawdown profiles separate in simulation handoff.
