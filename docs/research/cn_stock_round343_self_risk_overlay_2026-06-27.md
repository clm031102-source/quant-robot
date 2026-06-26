# CN Stock Round343 - Self Risk Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round343 attacks the remaining 2017-2018 regime loss without using future information.

Base candidate:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

The overlay decision uses only strategy returns already closed before each `decision_date`.

Output:

`data/reports/round343_24h_profit_sprint_self_risk_overlay_20260627`

2026 final holdout remains unused.

## Rules Tested

| Policy | Rule |
|---|---|
| `baseline_vol_target_6` | No extra self-risk overlay |
| `roll21_sum_neg_half` | Half exposure when prior 21-event return sum is negative |
| `roll21_sum_m2_cash` | Cash when prior 21-event return sum is below -2% |
| `roll42_sum_neg_half` | Half exposure when prior 42-event return sum is negative |
| `roll42_sum_m3_half` | Half exposure when prior 42-event return sum is below -3% |
| `current_dd_10_half` | Half exposure when current prior drawdown is below -10% |
| `current_dd_15_cash` | Cash when current prior drawdown is below -15% |
| `combo_roll21_neg_or_dd10_half` | Half exposure when prior 21-event sum is negative or prior drawdown is below -10% |
| `combo_roll21_m2_cash_dd10_half` | Cash when prior 21-event sum is below -2%; otherwise half exposure when prior drawdown is below -10% |

## Full-Sample Result

| Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Guard Exposure |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_vol_target_6` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | 100.00% |
| `roll42_sum_m3_half` | +156.40% | +5.85% | 0.964 | 0.524 | -20.68% | 89.33% |
| `current_dd_10_half` | +132.97% | +5.24% | 0.900 | 0.476 | -20.40% | 88.79% |
| `roll42_sum_neg_half` | +128.19% | +5.11% | 0.888 | 0.470 | -18.93% | 84.17% |
| `combo_roll21_m2_cash_dd10_half` | +76.08% | +3.48% | 0.662 | 0.330 | -16.19% | 68.47% |

## 2017-2018 Stress Period

| Policy | 2017-2018 Total | 2017-2018 Ann. | 2017-2018 Overlap | 2017-2018 DD |
|---|---:|---:|---:|---:|
| `baseline_vol_target_6` | -24.36% | -6.86% | -1.014 | -28.88% |
| `roll42_sum_m3_half` | -17.08% | -4.66% | -0.934 | -20.68% |
| `roll42_sum_neg_half` | -15.26% | -4.13% | -0.863 | -18.93% |
| `current_dd_10_half` | -16.79% | -4.57% | -0.833 | -20.40% |
| `combo_roll21_m2_cash_dd10_half` | -9.78% | -2.59% | -0.570 | -12.18% |

## Cross-Split Robustness

Aggregated across 30 one-year test folds from train/test schemes 2/1, 3/1, 4/1, and 5/1.

| Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|
| `baseline_vol_target_6` | +7.86% | -10.66% | 0.845 | -24.00% | 90.00% |
| `roll42_sum_m3_half` | +6.29% | -6.22% | 0.772 | -15.12% | 76.67% |
| `current_dd_10_half` | +5.43% | -6.17% | 0.762 | -14.93% | 76.67% |
| `roll42_sum_neg_half` | +4.87% | -5.29% | 0.667 | -15.12% | 76.67% |
| `combo_roll21_m2_cash_dd10_half` | +1.96% | -5.73% | 0.363 | -16.19% | 40.00% |

## Interpretation

Self-risk overlays do reduce the 2017-2018 damage, but they do not improve the primary return objective.

Best balanced defensive overlay:

`roll42_sum_m3_half`

Why:

- full-sample overlap Sharpe is slightly higher than baseline: 0.524 vs 0.517;
- full-sample max drawdown improves from -28.88% to -20.68%;
- 2017-2018 drawdown improves from -28.88% to -20.68%;
- total return remains high at +156.40%, but it is below the baseline +177.08%.

Best crash-control overlay:

`combo_roll21_m2_cash_dd10_half`

Why it is not the default:

- 2017-2018 drawdown improves to -12.18%;
- full-sample total return collapses to +76.08%;
- OOS strict pass drops to 40.00%.

## Decision

Do not replace the primary candidate.

Keep:

`replace_drop_turnover_f_low10 + vol_target_6_lb84`

Add optional defensive variant:

`replace_drop_turnover_f_low10 + vol_target_6_lb84 + roll42_sum_m3_half`

This variant is useful if the simulation stage prioritizes drawdown control over maximum total return.

Reject:

- `roll21_sum_m2_cash`;
- `current_dd_15_cash`;
- `combo_roll21_m2_cash_dd10_half` as default.

Next work should test external market-regime information rather than only self-equity rules, because self-risk guards reduce damage but mostly trade away return.
