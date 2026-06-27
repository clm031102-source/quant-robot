# CN Stock Round401 - Qlib Alpha101 Tilt Self-Risk

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round401 applied the reusable self-risk overlay suite to the Qlib Alpha101 selected-entry tilt candidates from Round398/399.

Input event streams:

- `qlib_top10_m150_vt6_zz500_mult_1.00`
- `qlib_top15_m150_vt6_zz500_mult_1.00`

Output:

`data/reports/round401_24h_profit_sprint_qlib_alpha101_tilt_self_risk_20260627`

## Full-Sample Result

| Candidate | Policy | Total | Ann. | Overlap | Max DD | Avg Exposure | Guard Share |
|---|---|---:|---:|---:|---:|---:|---:|
| `qlib_top15_m150_self_roll21_sum_m2_cash` | cash when prior 21-event sum < -2% | 2.1851 | 7.25% | 0.630 | -14.02% | 70.38% | 29.62% |
| `qlib_top15_m150_self_roll21_sum_neg_half` | half when prior 21-event sum < 0 | n/a | 7.13% | 0.604 | -17.12% | 80.70% | 38.61% |
| `qlib_top10_m150_self_roll21_sum_neg_half` | half when prior 21-event sum < 0 | 2.0917 | 7.06% | 0.615 | -16.14% | 80.64% | 38.73% |
| `qlib_top10_m150_self_roll21_sum_m2_cash` | cash when prior 21-event sum < -2% | 2.0600 | 6.99% | 0.618 | -15.12% | 70.98% | 29.02% |
| `qlib_top10_m150` | baseline | 1.9015 | 6.65% | 0.522 | -29.79% | 100.00% | 0.00% |

## Interpretation

Self-risk materially improved the Qlib tilt. It reduced drawdown and improved risk-adjusted metrics while preserving or increasing full-sample return.

However, the best-looking full-sample rule (`top15_m150 + roll21_sum_m2_cash`) must be audited OOS before promotion because it cuts exposure more aggressively and can overfit regime timing.

## Decision

Advance the following candidates to Round402 audit:

- `qlib_top15_m150_self_roll21_sum_m2_cash`
- `qlib_top10_m150_self_roll21_sum_neg_half`
- `qlib_top10_m150_self_roll21_sum_m2_cash`

Use `dragon_hot_100` and `dragon_hot_100_self_roll21_sum_neg_half` as references.
