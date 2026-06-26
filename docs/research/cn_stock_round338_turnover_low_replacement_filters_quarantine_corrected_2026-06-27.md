# CN Stock Round338 - Quarantine-Corrected Turnover-Low Replacement Filters

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Correction Note

Round337 was an invalid first pass because it did not apply the same data-quality quarantine used by Round322/Round333:

- exclude `CN_XBEI`;
- quarantine assets with absolute daily return above 50%.

That expanded the candidate universe and changed the selected assets. Round337 is therefore not promotion evidence.

Round338 reruns the replacement-filter idea with the correct quarantine. The corrected data window matches Round322:

- remaining assets: 1,749;
- remaining bar rows: 2,080,010;
- factor rows after rebalance filtering: 393,140;
- baseline `replace_no_extra_filter` matches Round322/Round333 exactly.

Output:

`data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627`

2026 final holdout remains unused.

## Hypothesis

Previous cash filtering improved drawdown but reduced exposure. This round tests replacement:

1. start from `turnover_rate_low` Top50;
2. remove undesirable candidates from the candidate universe before ranking;
3. refill Top50 with the next best low-turnover names;
4. then apply the same entry-tradeability cash proxy.

## Baselines

| Baseline | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| `entry_cash_no_extra_filter` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% |
| `cash_low_turnover_f_bottom20` | +107.79% | +4.52% | 0.750 | 0.414 | -28.01% |

## Full-Sample Results

2015-2025, Top50, hold20, rebalance5, cost5 bps, entry-cash tradeability.

| Variant | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Entry Allowed |
|---|---:|---:|---:|---:|---:|---:|
| `replace_drop_turnover_f_low30` | +177.55% | +6.36% | 0.828 | 0.459 | -39.73% | 19,421 |
| `replace_drop_turnover_f_low20_or_pb_high20` | +164.42% | +6.05% | 0.788 | 0.437 | -40.81% | 20,151 |
| `replace_drop_turnover_f_low10` | +150.65% | +5.71% | 0.779 | 0.428 | -35.29% | 20,382 |
| `replace_drop_turnover_f_low20_or_pe_high20` | +149.91% | +5.69% | 0.765 | 0.420 | -36.51% | 19,865 |
| `replace_drop_turnover_f_low20` | +141.82% | +5.48% | 0.730 | 0.401 | -38.78% | 20,009 |

## Cross-Split Robustness

Aggregated over train/test split schemes 2/1, 3/1, 4/1, and 5/1.

| Variant | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `replace_drop_turnover_f_low20_or_pb_high20` | +9.96% | +6.99% | 1.027 | 0.646 | -21.26% | 90.18% |
| `replace_drop_turnover_f_low30` | +10.16% | +7.01% | 1.000 | 0.606 | -20.83% | 90.18% |
| `replace_drop_turnover_f_low20_or_ps_high20` | +8.54% | +5.76% | 0.900 | 0.530 | -21.86% | 74.32% |
| `replace_drop_turnover_f_low20` | +8.21% | +5.62% | 0.822 | 0.476 | -20.47% | 74.32% |
| `replace_drop_turnover_f_low10` | +8.28% | +5.72% | 0.740 | 0.403 | -20.22% | 74.32% |

## Regime Audit

The replacement filters improve 2019-2025 strongly, but they do not solve 2017-2018.

| Variant | 2017-2018 Ann. | 2017-2018 Max DD | 2019-2020 Ann. | 2023-2025 Ann. |
|---|---:|---:|---:|---:|
| `replace_no_extra_filter` | -6.48% | -26.80% | +9.15% | +9.40% |
| `replace_drop_turnover_f_low10` | -6.85% | -28.85% | +12.58% | +9.91% |
| `replace_drop_turnover_f_low20` | -7.73% | -31.36% | +15.45% | +11.09% |
| `replace_drop_turnover_f_low30` | -7.90% | -32.68% | +13.73% | +15.96% |
| `replace_drop_turnover_f_low20_or_pb_high20` | -7.61% | -32.12% | +14.60% | +14.30% |

## Decision

This is the first materially useful new direction after the turnover repair line:

- replacement beats simple cash filtering on return and OOS overlap;
- `replace_drop_turnover_f_low10` is the most conservative replacement candidate;
- `replace_drop_turnover_f_low20_or_pb_high20` and `replace_drop_turnover_f_low30` are high-return research candidates but have unacceptable full-sample drawdown around 40%.

Do not promote yet. The next step is to pair replacement with the corrected calendar-aware risk wrappers from Round335, especially `vol_target_5_lb84` and `vol_target_4_lb168`, and compare against `cash_low_turnover_f_bottom20`.

## Candidate Status

Research candidates:

- conservative: `replace_drop_turnover_f_low10`;
- return-seeking: `replace_drop_turnover_f_low20_or_pb_high20`;
- stress candidate: `replace_drop_turnover_f_low30`.

Promotion status: not paper-ready, not simulation-ready until the wrapper test confirms drawdown control without destroying OOS return.
