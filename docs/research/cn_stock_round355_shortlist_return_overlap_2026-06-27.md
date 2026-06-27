# CN Stock Round355 - Shortlist Return Overlap Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round355 checks whether the current simulation shortlist represents meaningfully different return streams or merely many names for the same signal.

Output:

`data/reports/round355_24h_profit_sprint_shortlist_return_overlap_20260627`

2026 final holdout remains unused.

## Candidates

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| `primary_high_return` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% |
| `primary_balanced_zz500_75` | +161.99% | +5.99% | 0.989 | 0.530 | -24.74% |
| `primary_defensive_zz500` | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% |
| `primary_ps_filtered_defensive_zz500` | +119.29% | +4.86% | 1.076 | 0.573 | -15.90% |
| `safer_defensive_zz500` | +114.76% | +4.73% | 0.996 | 0.534 | -14.94% |

## Pearson Correlation

| Pair | Corr. |
|---|---:|
| `primary_high_return` vs `primary_balanced_zz500_75` | 0.991 |
| `primary_high_return` vs `primary_defensive_zz500` | 0.957 |
| `primary_high_return` vs `primary_ps_filtered_defensive_zz500` | 0.943 |
| `primary_high_return` vs `safer_defensive_zz500` | 0.905 |
| `primary_defensive_zz500` vs `primary_ps_filtered_defensive_zz500` | 0.988 |
| `primary_ps_filtered_defensive_zz500` vs `safer_defensive_zz500` | 0.956 |

## Interpretation

The current shortlist is not five independent alpha discoveries.

It is one useful primary signal family with several risk forms:

- 100% exposure: highest return;
- 75% CSI500 risk-off: balanced return/risk;
- 50% CSI500 risk-off: defensive default;
- PS-selected cash filter plus 50% risk-off: lower-drawdown defensive observation;
- safer cash-bottom20 variant: low-drawdown reference.

This is still valuable, but the project should be honest about it. The shortlist is a simulation lane stack, not a diversified multi-factor model.

## Preference Scores

The score below is only a decision aid, not a promotion gate.

| Candidate | Return-Seeking | Balanced | Defensive |
|---|---:|---:|---:|
| `primary_high_return` | 0.880 | 0.573 | 0.367 |
| `primary_balanced_zz500_75` | 0.846 | 0.584 | 0.405 |
| `primary_defensive_zz500` | 0.807 | 0.590 | 0.439 |
| `primary_ps_filtered_defensive_zz500` | 0.736 | 0.588 | 0.482 |
| `safer_defensive_zz500` | 0.707 | 0.561 | 0.456 |

The ranking is intuitive:

- return-seeking: `primary_high_return`;
- balanced: `primary_defensive_zz500` and `primary_ps_filtered_defensive_zz500` are close;
- defensive: `primary_ps_filtered_defensive_zz500`.

## Decision

Keep all five only for simulation comparison, not as five separate promoted factors.

Simulation lane labels:

- `primary_high_return`: return lane;
- `primary_balanced_zz500_75`: middle-risk lane;
- `primary_defensive_zz500`: default defensive lane;
- `primary_ps_filtered_defensive_zz500`: quality-filter defensive lane;
- `safer_defensive_zz500`: low-drawdown reference.

Next work:

- avoid counting these as independent discoveries;
- next alpha mining should seek a genuinely orthogonal source or mechanism;
- if no orthogonal source is available, improve execution/risk controls around this primary family instead of pretending a new factor exists.
