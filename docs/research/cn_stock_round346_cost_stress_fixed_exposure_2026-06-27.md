# CN Stock Round346 - Cost Stress With Fixed Official Exposure

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round346 tests cost sensitivity for the primary and aggressive candidates.

Important correction:

The first Round346 output at

`data/reports/round346_24h_profit_sprint_cost_stress_primary_aggressive_20260627`

is not evidence. It tried to recompute volatility-target exposure and failed to reproduce the official current-cost event stream.

The corrected output is:

`data/reports/round346_24h_profit_sprint_cost_stress_fixed_exposure_corrected_20260627`

This corrected version freezes the official volatility-target exposure from Round339, reconstructs event returns from trade `gross_return` and `target_weight`, and then stresses cost drag.

Validation:

| Candidate | Current-Cost Reproduction Max Abs Diff |
|---|---:|
| `primary_low10_vol6` | 1.84e-16 |
| `aggressive_low20_pb_vol5` | 1.73e-16 |

## Cost Grid

Cost rates tested:

- 5 bps equivalent: 0.0005;
- 10 bps equivalent: 0.0010;
- 20 bps equivalent: 0.0020;
- 30 bps equivalent: 0.0030.

Regime policies:

- `baseline`;
- `zz500_mom120_neg_half`.

2026 final holdout remains unused.

## Primary Candidate

`primary_low10_vol6`

| Cost | Regime | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---:|---|---:|---:|---:|---:|---:|
| 5 bps | `baseline` | +190.19% | +6.65% | 1.001 | 0.539 | -28.40% |
| 5 bps | `zz500_mom120_neg_half` | +156.16% | +5.85% | 1.038 | 0.556 | -20.02% |
| 10 bps | `baseline` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% |
| 10 bps | `zz500_mom120_neg_half` | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% |
| 20 bps | `baseline` | +152.60% | +5.76% | 0.877 | 0.472 | -29.83% |
| 20 bps | `zz500_mom120_neg_half` | +130.44% | +5.17% | 0.927 | 0.497 | -21.10% |
| 30 bps | `baseline` | +130.29% | +5.17% | 0.793 | 0.427 | -30.77% |
| 30 bps | `zz500_mom120_neg_half` | +114.75% | +4.73% | 0.852 | 0.457 | -21.81% |

## Primary Cross-Split

| Cost | Regime | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---:|---|---:|---:|---:|---:|---:|
| 5 bps | `baseline` | +8.29% | -10.47% | 0.892 | -23.75% | 90.00% |
| 5 bps | `zz500_mom120_neg_half` | +6.37% | -6.09% | 0.872 | -14.70% | 90.00% |
| 10 bps | `baseline` | +7.86% | -10.66% | 0.845 | -24.00% | 90.00% |
| 10 bps | `zz500_mom120_neg_half` | +6.05% | -6.22% | 0.824 | -14.87% | 90.00% |
| 20 bps | `baseline` | +7.01% | -11.05% | 0.752 | -24.49% | 76.67% |
| 20 bps | `zz500_mom120_neg_half` | +5.41% | -6.47% | 0.727 | -15.21% | 90.00% |
| 30 bps | `baseline` | +6.18% | -11.44% | 0.659 | -24.98% | 63.33% |
| 30 bps | `zz500_mom120_neg_half` | +4.78% | -6.72% | 0.630 | -15.54% | 90.00% |

## Interpretation

The primary candidate is cost-sensitive but not cost-fragile.

At 30 bps equivalent, the high-return baseline still has positive full-sample total return of +130.29%, but its quality degrades:

- overlap Sharpe falls from 0.517 to 0.427;
- full-sample max drawdown breaches 30%;
- cross-split strict pass falls from 90.00% to 63.33%.

The defensive external-regime variant has lower return but better cost robustness:

- at 30 bps, total return remains +114.75%;
- max drawdown stays near -21.81%;
- strict pass remains 90.00%.

## Decision

Keep the high-return default:

`primary_low10_vol6 baseline`

Use the defensive variant for stricter cost/slippage simulation:

`primary_low10_vol6 + zz500_mom120_neg_half`

Do not use the aggressive candidate as default after cost stress. It remains viable as a research comparison, but it does not dominate the primary candidate once the same external regime and cost stress are applied.

Next required check:

- benchmark/beta dependence for the three simulation tiers.
