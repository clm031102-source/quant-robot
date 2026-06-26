# CN Stock Round339 - Replacement Filters + Volatility-Target Wrappers

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round338 found that replacement filters materially improve return and OOS overlap, but full-sample drawdown remains too high. Round339 tests whether Round335 volatility-target wrappers can control drawdown without destroying the replacement edge.

Output:

`data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627`

2026 final holdout remains unused.

## Filters Tested

- `cash_low_turnover_f_bottom20`
- `replace_no_extra_filter`
- `replace_drop_turnover_f_low10`
- `replace_drop_turnover_f_low20`
- `replace_drop_turnover_f_low30`
- `replace_drop_turnover_f_low20_or_pb_high20`

Wrappers:

- `no_overlay`
- `vol_target_4_lb168`
- `vol_target_5_lb84`
- `vol_target_6_lb84`
- `vol_target_7_lb63`

## Best Full-Sample Rows

2015-2025, full 834-event calendar, entry-date decision alignment.

| Filter | Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---|---:|---:|---:|---:|---:|---:|
| `cash_low_turnover_f_bottom20` | `vol_target_5_lb84` | +137.10% | +5.36% | 0.984 | 0.533 | -21.98% | 90.35% |
| `replace_drop_turnover_f_low10` | `vol_target_6_lb84` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | 89.15% |
| `replace_drop_turnover_f_low20_or_pb_high20` | `vol_target_5_lb84` | +168.73% | +6.16% | 0.953 | 0.514 | -31.83% | 82.76% |
| `replace_drop_turnover_f_low10` | `vol_target_5_lb84` | +167.26% | +6.12% | 0.965 | 0.514 | -28.97% | 84.26% |
| `replace_drop_turnover_f_low30` | `vol_target_5_lb84` | +166.00% | +6.09% | 0.946 | 0.513 | -32.45% | 82.73% |

## Cross-Split Robustness

Aggregated over train/test split schemes 2/1, 3/1, 4/1, and 5/1.

| Filter | Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Strict Pass |
|---|---|---:|---:|---:|---:|---:|---:|
| `replace_drop_turnover_f_low20_or_pb_high20` | `vol_target_4_lb168` | +10.04% | +7.04% | 1.031 | 0.645 | -21.26% | 90.18% |
| `replace_drop_turnover_f_low20_or_pb_high20` | `no_overlay` | +9.96% | +6.99% | 1.027 | 0.646 | -21.26% | 90.18% |
| `replace_drop_turnover_f_low30` | `vol_target_4_lb168` | +10.26% | +7.10% | 1.009 | 0.615 | -20.83% | 90.18% |
| `replace_drop_turnover_f_low20_or_pb_high20` | `vol_target_5_lb84` | +8.26% | +5.62% | 0.951 | 0.583 | -19.37% | 90.18% |
| `replace_drop_turnover_f_low10` | `vol_target_6_lb84` | +7.24% | +4.83% | 0.688 | 0.356 | -20.10% | 74.32% |

## Regime Audit

The balanced candidate is:

`replace_drop_turnover_f_low10 + vol_target_6_lb84`

| Period | Ann. | Overlap Sharpe | Max DD | Total |
|---|---:|---:|---:|---:|
| 2015-2016 | +12.48% | 0.768 | -13.88% | +75.51% |
| 2017-2018 | -6.86% | -1.014 | -28.88% | -24.36% |
| 2019-2020 | +11.58% | 0.977 | -6.93% | +30.09% |
| 2021-2022 | +9.79% | 1.090 | -15.12% | +22.83% |
| 2023-2025 | +8.61% | 0.900 | -12.18% | +30.62% |

It still fails in 2017-2018, but it keeps the loss inside the user's stated approximate drawdown tolerance while producing much stronger total and annualized return than the cash baseline.

## Decision

Current best balanced research candidate:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Why it matters:

- full-sample total return improves from +137.10% for the safer cash baseline to +177.08%;
- full-sample annualized return improves from +5.36% to +6.35%;
- max drawdown stays below 30%;
- OOS remains positive across split schemes, though weaker than the more aggressive `low20_or_pb` family.

Current safer benchmark:

`cash_low_turnover_f_bottom20 + vol_target_5_lb84`

Why it remains useful:

- strongest full-sample overlap Sharpe;
- much lower max drawdown near -22%;
- better conservative fallback if simulation requires tighter risk.

## Next Step

Before simulation:

1. run a final promotion-style comparison between the balanced candidate and the safer benchmark;
2. add turnover/capacity summaries for both;
3. keep 2026 holdout sealed unless explicitly doing final read-once validation.
