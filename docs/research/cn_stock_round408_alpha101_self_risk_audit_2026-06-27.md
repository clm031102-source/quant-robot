# CN Stock Round408 - Alpha101 Self-Risk Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round408 audited the Round407 self-risk candidates against OOS splits, block dependence, and ZZ500 beta exposure. Qlib self-risk and Dragon-Hot self-risk were included as references.

## Outputs

- OOS: `data/reports/round408_24h_profit_sprint_alpha101_self_risk_oos_20260627`
- Block audit: `data/reports/round408_24h_profit_sprint_alpha101_self_risk_block_audit_20260627`
- Beta audit: `data/reports/round408_24h_profit_sprint_alpha101_self_risk_beta_audit_20260627`

## Key Result

The full-sample winner was not the best promotion candidate:

- `alpha_tilt_open_m2cash` and `alpha_tilt_vwap_m2cash` had strong full-sample metrics but only 76.7% strict OOS pass.
- `alpha_tilt_open_neghalf` preserved high return and passed 90% strict OOS.

## Stable Alpha101 Candidate

`alpha_tilt_open_neghalf`

- total return: +232.15%
- annualized return: 7.52%
- Sharpe: 1.229
- overlap Sharpe: 0.645
- max drawdown: -16.45%
- leave-one-year min annualized return: 5.02%
- mean OOS annualized return: 8.05%
- mean OOS overlap Sharpe: 0.916
- worst OOS drawdown: -13.44%
- strict OOS pass rate: 90%
- ZZ500 beta: 0.0354
- beta-hedged annualized return: 7.49%
- beta-hedged overlap Sharpe: 1.023
- beta-hedged max drawdown: -9.71%

## Reference Comparison

| Candidate | Annualized | Overlap Sharpe | Max DD | Mean OOS Ann. | Worst OOS DD | Hedged Overlap |
|---|---:|---:|---:|---:|---:|---:|
| `alpha_tilt_open_neghalf` | 7.52% | 0.645 | -16.45% | 8.05% | -13.44% | 1.023 |
| `qlib_top10_m150_self_neghalf` | 7.06% | 0.615 | -16.14% | 7.60% | -13.48% | 0.965 |
| `dragon_hot_self_neghalf` | 6.71% | 0.617 | -15.46% | 7.20% | -12.75% | 0.979 |

## Decision

Advance `alpha_tilt_open_neghalf` to Round409 marginal-value audit.

Reject `m2_cash` for shortlist despite strong full-sample metrics because OOS strict pass is only 76.7%.
