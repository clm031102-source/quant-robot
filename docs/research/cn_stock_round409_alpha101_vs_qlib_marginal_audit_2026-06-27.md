# CN Stock Round409 - Alpha101 Versus Qlib Marginal Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round409 tested whether the Alpha101 self-risk candidate adds independent value versus the existing Qlib self-risk lane, or whether it is mostly a correlated replacement.

Output: `data/reports/round409_24h_profit_sprint_alpha101_vs_qlib_marginal_audit_20260627`

## Correlation

Pearson correlation to `qlib_top10_m150_self_neghalf`:

| Candidate | Correlation |
|---|---:|
| `alpha_tilt_open_neghalf` | 0.9950 |
| `alpha_cash_open100_neghalf` | 0.9876 |
| `dragon_hot_self_neghalf` | 0.9973 |
| `alpha_tilt_open_m2cash_oos_trap` | 0.9427 |

The Alpha101 stable candidate is not an independent family in portfolio-return space. It is a highly correlated variant of the same Dragon-Hot/public open-close risk-budget lane.

## Marginal Value Versus Qlib

`alpha_tilt_open_neghalf` versus `qlib_top10_m150_self_neghalf`:

- annualized return diff proxy: +0.11%
- positive diff rate: 39.45%
- diff t-stat: 2.94
- correlation: 0.9950

Interpretation: Alpha101 has a small but measurable edge over Qlib in this sample, but it is not diversified alpha.

## Combo Check

Simple 50/50 combinations did not dominate the best single Alpha101 self-risk candidate:

- `alpha_tilt_open_neghalf`: annualized 7.52%, overlap 0.645, max drawdown -16.45%
- 50/50 Alpha101 + Qlib: annualized 7.29%, overlap 0.630, max drawdown -16.26%
- 50/50 Alpha101 + cash-filter Alpha101: annualized 7.07%, overlap 0.656, max drawdown -15.46%

## Decision

Add `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` as a simulation risk-budget observation.

Do not call it a new independent factor family. Treat it as a potentially stronger replacement/variant for Qlib self-risk during simulation comparison.
