# CN Stock Round340 - Candidate Comparison Pack

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round340 packages the current simulation candidates into one comparable table:

- balanced candidate;
- safer drawdown benchmark;
- aggressive research-only candidate.

Output:

`data/reports/round340_24h_profit_sprint_candidate_comparison_pack_20260627`

2026 final holdout remains unused.

## Decision

Primary simulation candidate:

`balanced_replacement_low10_vol6`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Risk benchmark:

`safer_cash_low_turnover_f_bottom20_vol5`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost5 + cash_low_turnover_f_bottom20 + entry_cash + vol_target_5_lb84`

Research-only aggressive candidate:

`aggressive_replace_low20_pb_vol5`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low20_or_pb_high20 + entry_cash + vol_target_5_lb84`

## Comparison

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Balanced `low10 + vol6` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | +7.24% | 0.688 | -20.10% |
| Safer cash benchmark | +137.10% | +5.36% | 0.984 | 0.533 | -21.98% | +5.53% | 0.639 | -16.13% |
| Aggressive `low20_or_pb + vol5` | +168.73% | +6.16% | 0.953 | 0.514 | -31.83% | +8.26% | 0.951 | -19.37% |

## Tradeability And Capacity

| Candidate | Entry Allowed | Entry Blocked | Blocked Rate | Avg Participation | Max Participation | Capacity-Limited Trades |
|---|---:|---:|---:|---:|---:|---:|
| Balanced `low10 + vol6` | 20,382 | 6,068 | 22.94% | 0.0129% | 0.2728% | 0 |
| Safer cash benchmark | 20,841 | 5,609 | 21.21% | 0.0125% | 0.4579% | 0 |
| Aggressive `low20_or_pb + vol5` | 20,151 | 6,299 | 23.81% | 0.0132% | 1.3342% | 0 |

Capacity is not currently the blocker at the tested 1,000,000 portfolio value and 5% max participation cap. The bigger practical issue is tradeability blocking and 2017-2018 regime loss.

## Regime Comparison

| Candidate | 2017-2018 Ann. | 2017-2018 DD | 2019-2020 Ann. | 2021-2022 Ann. | 2023-2025 Ann. |
|---|---:|---:|---:|---:|---:|
| Balanced `low10 + vol6` | -6.86% | -28.88% | +11.58% | +9.79% | +8.61% |
| Safer cash benchmark | -5.03% | -21.98% | +7.78% | +6.98% | +7.84% |
| Aggressive `low20_or_pb + vol5` | -7.58% | -31.83% | +11.87% | +8.91% | +10.61% |

## Interpretation

The balanced candidate is not the lowest-risk option, but it is the best current trade-off for the user's stated preference: higher total return and annualized return are valuable, and drawdown around 30% is acceptable.

The safer benchmark remains important because it has better full-sample overlap Sharpe and materially lower drawdown.

The aggressive candidate has attractive OOS statistics but exceeds the 30% full-sample drawdown line. It stays research-only for now.

## Next Work

Before treating the balanced candidate as simulation-ready:

1. run threshold sensitivity around `turnover_rate_f` exclusions: 5%, 10%, 15%, 20%;
2. confirm no single threshold dominates only by luck;
3. keep the candidate frozen if 10% remains robust;
4. leave 2026 holdout untouched until read-once final validation.
