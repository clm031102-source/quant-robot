# CN Stock Round351 - ZZ500 75% Cost/Beta Quickcheck

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round350 found that the CSI500 risk-off multiplier at 75% is a useful middle point between:

- `primary_high_return`: no CSI500 risk-off cut;
- `primary_defensive_zz500`: 50% exposure when CSI500 120-day momentum is negative.

Round351 checks whether the 75% version survives two practical filters:

- fixed official-exposure cost stress at 5/10/20/30 bps;
- benchmark beta audit versus HS300 and CSI500 at the current 10 bps cost rate.

Output:

`data/reports/round351_24h_profit_sprint_zz500_75_cost_beta_quickcheck_20260627`

2026 final holdout remains unused.

## Reproduction Checks

The quickcheck reconstructs official event returns from the Round341 trade parquet and freezes the official Round339 volatility-target exposure before applying cost and CSI500 regime exposure.

| Check | Max Abs Diff |
|---|---:|
| Official 10 bps current-cost event stream | 1.84e-16 |
| Round346 50% risk-off 10 bps stream | 9.99e-17 |
| Round346 100% baseline 10 bps stream | 9.97e-17 |
| Round350 75% risk-off 10 bps stream | 1.87e-16 |

This means the Round351 numbers are on the same event-return surface as the accepted Round346/Round350 evidence.

## 75% Cost Stress

Candidate:

`primary_low10_vol6 + zz500_mom120_neg_mult_0.75`

| Cost | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Final Exposure |
|---:|---:|---:|---:|---:|---:|---:|
| 5 bps | +172.88% | +6.25% | 1.029 | 0.552 | -24.31% | 79.25% |
| 10 bps | +161.99% | +5.99% | 0.989 | 0.530 | -24.74% | 79.25% |
| 20 bps | +141.48% | +5.47% | 0.909 | 0.488 | -25.58% | 79.25% |
| 30 bps | +122.57% | +4.95% | 0.829 | 0.445 | -26.42% | 79.25% |

## 75% Cross-Split

| Cost | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---:|---:|---:|---:|---:|---:|
| 5 bps | +7.32% | -8.30% | 0.876 | -19.34% | 90.00% |
| 10 bps | +6.95% | -8.46% | 0.828 | -19.55% | 90.00% |
| 20 bps | +6.21% | -8.78% | 0.732 | -19.97% | 90.00% |
| 30 bps | +5.47% | -9.10% | 0.637 | -20.40% | 76.67% |

## 10 bps Comparison

| Risk-Off Multiplier | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---:|---:|---:|---:|---:|---:|
| 50% | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% |
| 75% | +161.99% | +5.99% | 0.989 | 0.530 | -24.74% |
| 100% | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% |

The 75% setting keeps most of the return recovered from removing the defensive cut, while still reducing drawdown meaningfully versus the 100% baseline.

## Beta Quickcheck

Current cost rate: 10 bps.

| Risk-Off Multiplier | Benchmark | Beta | R2 | Strategy Ann. | Hedged Ann. | Hedged Overlap | Hedged DD |
|---:|---|---:|---:|---:|---:|---:|---:|
| 50% | HS300 | 0.0387 | 0.181 | +5.62% | +5.78% | 0.727 | -24.17% |
| 50% | CSI500 | 0.0329 | 0.234 | +5.62% | +5.59% | 0.890 | -12.50% |
| 75% | HS300 | 0.0432 | 0.194 | +5.99% | +6.18% | 0.722 | -26.08% |
| 75% | CSI500 | 0.0366 | 0.248 | +5.99% | +5.96% | 0.876 | -12.37% |
| 100% | HS300 | 0.0478 | 0.197 | +6.35% | +6.56% | 0.696 | -29.52% |
| 100% | CSI500 | 0.0403 | 0.251 | +6.35% | +6.32% | 0.826 | -13.40% |

The 75% candidate is not materially more beta-dominated than the 50% or 100% variants. CSI500 R2 remains near 0.25, and beta-hedged annualized return remains positive at about +5.96%.

## Decision

Add `primary_balanced_zz500_75` as a simulation observation lane, not as a replacement for the 50% defensive default.

Reason:

- compared with 50%, it improves total return from +147.29% to +161.99%;
- drawdown rises from -20.38% to -24.74%, still inside the user's stated tolerance around larger drawdowns;
- at 30 bps, it remains profitable, but strict pass falls to 76.67%, while 50% remains at 90.00%;
- beta profile stays similar to the accepted candidates.

Use:

- `primary_high_return`: return-seeking lane;
- `primary_balanced_zz500_75`: balanced return/risk lane;
- `primary_defensive_zz500`: defensive default;
- `safer_defensive_zz500`: low-drawdown reference.

Next work:

- search non-turnover factor families so the project does not keep optimizing one family forever;
- keep 2026 final holdout sealed until the simulation-readiness review.
