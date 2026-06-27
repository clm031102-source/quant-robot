# CN Stock Round402 - Qlib Alpha101 Tilt Self-Risk Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round402 audited the Qlib tilt self-risk candidates from Round401 with OOS split, block dependence, and benchmark beta diagnostics.

Outputs:

- OOS: `data/reports/round402_24h_profit_sprint_qlib_alpha101_tilt_self_risk_oos_20260627`
- Block: `data/reports/round402_24h_profit_sprint_qlib_alpha101_tilt_self_risk_block_audit_20260627`
- Beta: `data/reports/round402_24h_profit_sprint_qlib_alpha101_tilt_self_risk_beta_audit_20260627`

## Full-Sample And Block Audit

| Candidate | Total | Ann. | Sharpe | Overlap | Max DD | Leave-One-Year Min Ann. | Blockers |
|---|---:|---:|---:|---:|---:|---:|---|
| `qlib_top15_m150_self_m2_cash` | 2.1851 | 7.25% | 1.191 | 0.630 | -14.02% | 4.82% | none |
| `qlib_top10_m150_self_neg_half` | 2.0917 | 7.06% | 1.174 | 0.615 | -16.14% | 4.61% | none |
| `qlib_top10_m150_self_m2_cash` | 2.0600 | 6.99% | 1.171 | 0.618 | -15.12% | 4.60% | none |
| `dragon_hot_self_roll21` | 1.9310 | 6.71% | 1.173 | 0.617 | -15.46% | 4.42% | none |
| `dragon_hot_100` | 1.8120 | 6.45% | 0.987 | 0.532 | -28.57% | 3.96% | none |

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `dragon_hot_100` | 8.02% | 0.869 | -23.68% | 90.0% |
| `qlib_top10_m150_self_neg_half` | 7.60% | 0.854 | -13.48% | 90.0% |
| `dragon_hot_self_roll21` | 7.20% | 0.854 | -12.75% | 90.0% |
| `qlib_top15_m150_self_m2_cash` | 6.73% | 0.770 | -14.02% | 76.7% |
| `qlib_top10_m150_self_m2_cash` | 6.39% | 0.761 | -15.12% | 76.7% |

OOS rejects the most attractive full-sample rule as a primary observation. The more stable Qlib self-risk candidate is `qlib_top10_m150_self_neg_half`.

## Beta Audit

Against ZZ500:

| Candidate | Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|---:|
| `qlib_top15_m150_self_m2_cash` | 0.0307 | 0.1766 | 7.22% | 0.904 | -12.58% |
| `qlib_top10_m150_self_neg_half` | 0.0349 | 0.2334 | 7.02% | 0.965 | -10.14% |
| `dragon_hot_self_roll21` | 0.0333 | 0.2348 | 6.68% | 0.979 | -9.49% |

The Qlib top10 self-risk lane improves hedged annualized return versus Dragon-Hot self-risk while keeping beta and R2 close to the existing risk-budget profile.

## Decision

Add `primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150_self_roll21` as a simulation high-return risk-budget observation.

Do not add `qlib_top15_m150_self_m2_cash` as the preferred lane despite its strong full-sample result because OOS strict pass falls to 76.7%.
