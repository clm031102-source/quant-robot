# CN Stock Round395 - PS Dragon Self-Risk Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round395 tested whether the Round394 PS defensive filter becomes useful when paired with the existing self-risk overlay rules.

The goal is not to beat the high-return Dragon-Hot lane. The goal is to see whether PS plus self-risk creates a lower-drawdown profile worth carrying into simulation as a risk-control comparison.

## Outputs

- Overlay results: `data/reports/round395_24h_profit_sprint_ps_dragon_self_risk_20260627`
- OOS split: `data/reports/round395_24h_profit_sprint_ps_dragon_self_risk_oos_20260627`
- Block audit: `data/reports/round395_24h_profit_sprint_ps_dragon_self_risk_block_audit_20260627`
- Beta audit: `data/reports/round395_24h_profit_sprint_ps_dragon_self_risk_beta_audit_20260627`

## Best Rows

| Candidate | Ann. | Sharpe | Overlap | Max DD | Mean OOS Ann. | Worst OOS DD | CSI500 Hedged Ann. | CSI500 Hedged Overlap | CSI500 Hedged DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `dragon_hot_100_self_roll21_sum_neg_half` | 6.71% | 1.173 | 0.617 | -15.46% | 7.20% | -12.75% | 6.68% | 0.979 | -9.49% |
| `ps_dragon_100_self_roll21_sum_neg_half` | 5.76% | 1.199 | 0.634 | -13.17% | 5.95% | -10.29% | 5.72% | 0.999 | -7.78% |
| `ps_dragon_100_self_roll21_sum_m2_cash` | 5.82% | 1.208 | 0.648 | -10.43% | 5.41% | -10.43% | 5.79% | 0.952 | -10.15% |
| `ps_dragon_075_self_roll21_sum_neg_half` | 5.46% | 1.222 | 0.642 | -11.03% | 5.41% | -8.36% | 5.42% | 1.031 | -6.41% |

## Interpretation

The self-risk overlay remains the better improvement than the PS filter itself.

The best all-around high-return risk-budget line is still `dragon_hot_100_self_roll21_sum_neg_half`.

The best PS-derived low-drawdown candidate is `ps_dragon_100_self_roll21_sum_neg_half`: it keeps 90% strict OOS pass rate, lowers worst OOS drawdown to -10.29%, and has strong CSI500-hedged overlap at 0.999.

`ps_dragon_100_self_roll21_sum_m2_cash` has the lowest full-sample drawdown, but its OOS strict pass rate falls to 76.67%, so it is too defensive to prefer as the main observation.

## Decision

Add `ps_dragon_100_self_roll21_sum_neg_half` as an ultra-defensive simulation observation lane only.

Do not promote it as a profitable factor. It remains blocked from promotion by the Round394 projection mismatch until the official-template projection tolerance/calendar issue is repaired.
