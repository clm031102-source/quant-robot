# CN Stock Round354 - PS Filter Cost/Beta Quickcheck

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round354 validates the best Round353 defensive overlay:

`cash_ps_high20_selected`

Definition:

On each signal date, start from the selected `primary_low10_vol6` basket. Cash out selected entries whose `ps_ttm` is in the highest 20% of that selected basket. Do not replace them. Then apply the CSI500 120-day momentum risk-off overlay.

Output:

`data/reports/round354_24h_profit_sprint_ps_filter_cost_beta_quickcheck_20260627`

2026 final holdout remains unused.

## Reproduction Check

| Check | Max Abs Diff |
|---|---:|
| Base selected basket reproduces official 10 bps event stream | 1.84e-16 |

## PS Filter Cost Stress

### Risk-Off Multiplier 50%

| Cost | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---:|---:|---:|---:|---:|---:|
| 5 bps | +125.49% | +5.04% | 1.112 | 0.592 | -15.61% |
| 10 bps | +119.29% | +4.86% | 1.076 | 0.573 | -15.90% |
| 20 bps | +107.40% | +4.51% | 1.003 | 0.535 | -16.49% |
| 30 bps | +96.15% | +4.16% | 0.929 | 0.496 | -17.06% |

### Risk-Off Multiplier 75%

| Cost | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---:|---:|---:|---:|---:|---:|
| 5 bps | +136.93% | +5.35% | 1.099 | 0.589 | -19.11% |
| 10 bps | +129.42% | +5.15% | 1.059 | 0.568 | -19.46% |
| 20 bps | +115.11% | +4.74% | 0.980 | 0.526 | -20.15% |
| 30 bps | +101.69% | +4.33% | 0.901 | 0.483 | -20.84% |

## Cross-Split Cost Stress

| Risk-Off Mult. | Cost | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---:|---:|---:|---:|---:|---:|
| 50% | 5 bps | +5.26% | 0.909 | -11.88% | 90.00% |
| 50% | 10 bps | +5.01% | 0.862 | -12.02% | 90.00% |
| 50% | 20 bps | +4.52% | 0.766 | -12.30% | 90.00% |
| 50% | 30 bps | +4.02% | 0.671 | -12.57% | 76.67% |
| 75% | 10 bps | +5.67% | 0.879 | -15.75% | 76.67% |
| 75% | 30 bps | +4.52% | 0.686 | -16.45% | 76.67% |

## Beta Quickcheck

Current cost rate: 10 bps.

| Risk-Off Mult. | Benchmark | Beta | R2 | Strategy Ann. | Hedged Ann. | Hedged Overlap | Hedged DD |
|---:|---|---:|---:|---:|---:|---:|---:|
| 50% | HS300 | 0.0304 | 0.174 | +4.86% | +4.98% | 0.771 | -19.05% |
| 50% | CSI500 | 0.0259 | 0.226 | +4.86% | +4.83% | 0.943 | -9.32% |
| 75% | HS300 | 0.0340 | 0.187 | +5.15% | +5.28% | 0.769 | -20.60% |
| 75% | CSI500 | 0.0287 | 0.240 | +5.15% | +5.11% | 0.939 | -9.20% |

## Interpretation

The 50% PS-filtered candidate is a genuine defensive observation lane:

- it does not maximize return;
- it does improve overlap-adjusted Sharpe versus the existing defensive baseline;
- it keeps full-sample drawdown near -16%;
- it remains positive at 30 bps cost;
- CSI500 beta-hedged overlap is very strong at 0.943.

The trade-off is lower return and a 30 bps strict-pass drop from 90% to 76.67%.

## Decision

Add `primary_ps_filtered_defensive_zz500` as a simulation observation lane, not as the main default.

Recommended role:

- use it as the low-drawdown/quality-filter comparison against `safer_defensive_zz500`;
- do not replace `primary_defensive_zz500` unless the simulation objective prioritizes drawdown and hedged stability over annualized return.

Next work:

- add it to the packaged simulation shortlist;
- continue mining but avoid direct public anomaly TopN and direct forecast/express families unless a new source or mechanism appears.
