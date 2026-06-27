# CN Stock Round396 - PS-on-Dragon Threshold Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round396 tested whether the PS defensive result from Round394 is a single threshold artifact.

The tested cash filters were top 10%, 15%, 20%, 25%, and 30% PS within the post-Dragon-Hot selected basket.

## Outputs

- Projection sensitivity: `data/reports/round396_24h_profit_sprint_ps_on_dragon_threshold_sensitivity_20260627`
- Wrapped events: `data/reports/round396_24h_profit_sprint_ps_on_dragon_threshold_wrapped_20260627`
- OOS split: `data/reports/round396_24h_profit_sprint_ps_on_dragon_threshold_oos_20260627`
- Block audit: `data/reports/round396_24h_profit_sprint_ps_on_dragon_threshold_block_audit_20260627`
- Beta audit: `data/reports/round396_24h_profit_sprint_ps_on_dragon_threshold_beta_audit_20260627`

## Threshold Curve

| Candidate | Ann. | Sharpe | Overlap | Max DD | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | CSI500 Hedged Overlap | CSI500 Hedged DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `dragon_hot_100` | 6.45% | 0.987 | 0.532 | -28.57% | 8.02% | 0.869 | -23.68% | 0.843 | -13.28% |
| `ps_top10` | 6.09% | 1.002 | 0.547 | -26.99% | 7.62% | 0.935 | -22.40% | 0.868 | -12.82% |
| `ps_top15` | 5.90% | 1.016 | 0.552 | -25.81% | 7.16% | 0.912 | -21.29% | 0.879 | -12.47% |
| `ps_top20` | 5.72% | 1.048 | 0.569 | -23.60% | 6.88% | 0.937 | -19.48% | 0.901 | -10.95% |
| `ps_top25` | 5.44% | 1.065 | 0.580 | -21.79% | 6.38% | 0.939 | -18.07% | 0.930 | -10.05% |
| `ps_top30` | 5.18% | 1.090 | 0.599 | -19.98% | 6.00% | 0.956 | -16.73% | 0.962 | -9.32% |

## Interpretation

This is a smooth risk-return trade-off, not a single lucky parameter.

As the PS cash fraction increases, annualized return declines while overlap Sharpe and drawdown improve. That is economically plausible: expensive selected-basket names appear to add crash/drawdown risk rather than pure return alpha.

All PS thresholds still inherit the Round394 unmatched-contribution blocker. After the Round397 diagnostic upgrade, the PS top20 blocker is now interpretable:

- unmatched absolute flagged contribution: 0.0120;
- nonzero unmatched dates: 8;
- zero-contribution unmatched dates: 34;
- yearly unmatched absolute contribution: 2016 = 0.0023, 2018 = 0.0084, 2019 = 0.0014.

The blocker is stable across thresholds, so it is a projection/calendar issue to fix rather than a reason to tune the threshold further.

## Decision

Use PS-on-Dragon only as defensive profile construction evidence.

Preferred simulation observation from this family remains `ps_dragon_100_self_roll21_sum_neg_half`, because it combines:

- a stable PS defensive effect;
- the already useful self-risk overlay;
- 90% strict OOS pass rate;
- lower worst OOS drawdown than Dragon-Hot self-risk;
- strong CSI500-hedged overlap.

Do not continue PS threshold tuning unless the projection blocker is repaired first.
