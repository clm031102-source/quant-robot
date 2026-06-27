# CN Stock Round388 - Primary Self-Risk Cost Stress

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round388 tested whether the `roll21_sum_neg_half` self-risk rule remains useful under the corrected Round346 cost-stress event streams.

This is not a perfect cost rerun for the Dragon-Tiger lane. It applies the same self-risk rule to the corrected primary cost5/10/20/30 event streams. The goal is to test whether the risk-budget rule survives higher cost pressure on the core low-turnover family.

## Outputs

- Projection: `data/reports/round388_24h_profit_sprint_primary_self_risk_cost_stress_20260627`
- OOS split: `data/reports/round388_24h_profit_sprint_primary_self_risk_cost_stress_oos_20260627`

## Full-Sample Cost Stress

| Candidate | Ann. | Overlap | Max DD | Avg Exposure | Guard Share |
|---|---:|---:|---:|---:|---:|
| `primary_cost5_self_roll21_sum_neg_half` | 6.88% | 0.619 | -15.34% | 80.94% | 38.13% |
| `primary_cost5` | 6.65% | 0.539 | -28.40% | 100.00% | 0.00% |
| `primary_cost10_self_roll21_sum_neg_half` | 6.66% | 0.601 | -15.64% | 80.58% | 38.85% |
| `primary_cost10` | 6.35% | 0.517 | -28.88% | 100.00% | 0.00% |
| `primary_cost20_self_roll21_sum_neg_half` | 6.17% | 0.562 | -16.40% | 80.16% | 39.69% |
| `primary_cost20` | 5.76% | 0.472 | -29.83% | 100.00% | 0.00% |
| `primary_cost30_self_roll21_sum_neg_half` | 5.57% | 0.511 | -17.36% | 79.62% | 40.77% |
| `primary_cost30` | 5.17% | 0.427 | -30.77% | 100.00% | 0.00% |

The rule improves full-sample return, overlap Sharpe, and drawdown at every tested cost level.

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `primary_cost5` | 8.29% | 0.892 | -23.75% | 90.00% |
| `primary_cost5_self_roll21` | 7.43% | 0.873 | -12.79% | 90.00% |
| `primary_cost10` | 7.86% | 0.845 | -24.00% | 90.00% |
| `primary_cost10_self_roll21` | 7.10% | 0.834 | -12.93% | 90.00% |
| `primary_cost20` | 7.01% | 0.752 | -24.49% | 90.00% |
| `primary_cost20_self_roll21` | 6.39% | 0.748 | -13.22% | 90.00% |
| `primary_cost30` | 6.18% | 0.659 | -24.98% | 90.00% |
| `primary_cost30_self_roll21` | 5.52% | 0.638 | -13.52% | 76.67% |

OOS confirms the same pattern as Round387:

- self-risk sharply improves drawdown;
- baseline keeps higher mean OOS return;
- at 30 bps, the self-risk version loses OOS strict-pass breadth.

## Decision

Keep the Round387 interpretation:

`roll21_sum_neg_half` is a useful risk-budget overlay, not a default replacement for the high-return lane.

For simulation, this supports running two risk profiles side by side:

- high-return profile: `dragon_hot_100`;
- drawdown-controlled profile: `dragon_hot_100_self_roll21_sum_neg_half`.

Do not use the self-risk rule to claim higher expected live return unless future paper-simulation evidence confirms it. Its clearest value is drawdown control.

## Process Lesson

Cost stress should be run at the trade/gross/exposure layer whenever possible. Applying self-risk to already corrected event streams is acceptable as a rule sanity check, but not a substitute for a full Dragon-Tiger cost rerun from selected trades.
