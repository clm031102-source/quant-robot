# CN ETF Smart-Money Risk Overlay Round 18

Date: 2026-06-21

## Purpose

Round 18 tested whether the Round 17 ETF research lead survives a simple risk-control translation.

No new factor was invented. The test kept the same signal and parameters:

- Factor: `smart_money_trend_20`
- Market: `CN_ETF`
- TopN: 2
- Cost: 5 bps
- Rebalance interval: 5
- Regime lookback: 120

Only target gross exposure changed:

- Base Round 17: 0.8
- Round 18 probes: 0.6 and 0.5

## Configs

- `configs/experiment_grid_cn_etf_smart_money_risk_overlay_exposure06_20260621.json`
- `configs/experiment_grid_cn_etf_smart_money_risk_overlay_exposure05_20260621.json`

Outputs:

- `data/reports/experiment_grid_cn_etf_smart_money_risk_overlay_exposure06_20260621`
- `data/reports/experiment_grid_cn_etf_smart_money_risk_overlay_exposure05_20260621`

## Results

| Exposure | Decision | Total return | Relative return | Sharpe | Overlap Sharpe | Max DD | Win rate | Capacity-limited trades |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0.8 | rejected | 0.4705 | 0.1531 | 0.5737 | 0.6431 | -0.2589 | 0.5238 | 0 |
| 0.6 | approved | 0.3553 | 0.0379 | 0.5739 | 0.6434 | -0.1993 | 0.5238 | 0 |
| 0.5 | rejected | 0.2963 | -0.0211 | 0.5740 | 0.6435 | -0.1683 | 0.5238 | 0 |

## Interpretation

The 0.6 exposure version is the best current trade-off:

- It keeps positive benchmark-relative return.
- It reduces max drawdown below the 25% gate.
- It stays capacity-clean.
- It preserves the same Sharpe profile as the 0.8 version.

The 0.5 exposure version is too defensive:

- Drawdown improves, but benchmark-relative return turns negative.

## Important Caveat

The 0.6 row is only a validation candidate, not a promotable factor.

Reasons:

- RankIC t-stat is only about 1.43.
- IC evidence is not statistically significant.
- It has only passed a same-sample full-period gate.
- It still needs walk-forward / out-of-sample validation.
- ETF universe size is small, so IC may understate or be unstable; performance validation matters more here.

## Decision

Promote to next validation stage:

- `CN_ETF_smart_money_trend_20_top2_cost5_reb5_regime120`
- target gross exposure: 0.6

Do not promote to paper/live:

- Not enough out-of-sample evidence yet.

## Next Direction

Round 19 should run walk-forward validation for the 0.6 exposure candidate with the same frozen parameters.

If walk-forward fails:

- retire this as a full-sample overfit / market-regime artifact.

If walk-forward holds:

- run same-parameter replay and promotion-gate review.

## Current Conclusion

Round 18 produced 0 new factor names.

It produced the first current-cycle `approved` full-sample ETF validation candidate:

- `smart_money_trend_20`, Top2, cost 5 bps, rebalance 5, regime 120, target exposure 0.6.
