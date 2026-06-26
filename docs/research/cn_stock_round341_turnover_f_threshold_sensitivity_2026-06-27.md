# CN Stock Round341 - Turnover-F Threshold Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round341 tests whether the current balanced candidate depends on a lucky single threshold.

Base formula:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_lowXX + entry_cash`

Thresholds:

- 5%
- 10%
- 15%
- 20%

Policies:

- `no_overlay`
- `vol_target_6_lb84`

Output:

`data/reports/round341_24h_profit_sprint_turnover_f_threshold_sensitivity_20260627`

2026 final holdout remains unused.

## Full-Sample Results

2015-2025, full 834-event calendar, entry-date decision alignment.

| Threshold | Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---:|---|---:|---:|---:|---:|---:|---:|
| 5% | `no_overlay` | +141.18% | +5.46% | 0.751 | 0.409 | -35.25% | 100.00% |
| 10% | `no_overlay` | +150.65% | +5.71% | 0.779 | 0.428 | -35.29% | 100.00% |
| 15% | `no_overlay` | +152.34% | +5.75% | 0.771 | 0.423 | -37.06% | 100.00% |
| 20% | `no_overlay` | +141.82% | +5.48% | 0.730 | 0.401 | -38.78% | 100.00% |
| 5% | `vol_target_6_lb84` | +175.80% | +6.32% | 0.963 | 0.515 | -27.29% | 89.55% |
| 10% | `vol_target_6_lb84` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | 89.15% |
| 15% | `vol_target_6_lb84` | +172.65% | +6.25% | 0.934 | 0.504 | -30.69% | 88.54% |
| 20% | `vol_target_6_lb84` | +156.73% | +5.86% | 0.872 | 0.471 | -31.38% | 88.02% |

## Cross-Split Robustness

Aggregated over train/test split schemes 2/1, 3/1, 4/1, and 5/1.

| Threshold | Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Strict Pass |
|---:|---|---:|---:|---:|---:|---:|---:|
| 5% | `no_overlay` | +7.77% | +5.32% | 0.663 | 0.329 | -19.77% | 74.32% |
| 10% | `no_overlay` | +8.28% | +5.72% | 0.740 | 0.403 | -20.22% | 74.32% |
| 15% | `no_overlay` | +8.92% | +6.10% | 0.862 | 0.473 | -20.67% | 74.32% |
| 20% | `no_overlay` | +8.21% | +5.62% | 0.822 | 0.476 | -20.47% | 74.32% |
| 5% | `vol_target_6_lb84` | +7.05% | +4.70% | 0.626 | 0.296 | -19.77% | 74.32% |
| 10% | `vol_target_6_lb84` | +7.24% | +4.83% | 0.688 | 0.356 | -20.10% | 74.32% |
| 15% | `vol_target_6_lb84` | +7.74% | +5.10% | 0.805 | 0.422 | -20.55% | 74.32% |
| 20% | `vol_target_6_lb84` | +6.77% | +4.40% | 0.750 | 0.414 | -20.08% | 74.32% |

## Tradeability Summary

| Threshold | Entry Allowed | Entry Blocked | Excluded Candidate Rate | Avg Participation | Max Participation |
|---:|---:|---:|---:|---:|---:|
| 5% | 20,506 | 5,944 | 4.94% | 0.0129% | 0.4579% |
| 10% | 20,382 | 6,068 | 9.94% | 0.0129% | 0.2728% |
| 15% | 20,269 | 6,181 | 14.94% | 0.0128% | 0.2728% |
| 20% | 20,009 | 6,441 | 19.94% | 0.0126% | 0.2728% |

No threshold hits the 5% max participation cap at the tested 1,000,000 portfolio value.

## Interpretation

The replacement idea is not a single-threshold accident. The 5%, 10%, and 15% variants form a useful plateau:

- 5% has the lowest full-sample drawdown under `vol_target_6_lb84`, but weaker OOS overlap.
- 10% gives the best full-sample total return while staying below the user's approximate 30% drawdown tolerance.
- 15% gives the best OOS annualized return and OOS overlap, but full-sample drawdown breaches 30%.
- 20% is too aggressive: it removes more candidates while reducing full-sample return and increasing drawdown.

## Decision

Keep the current primary simulation candidate unchanged:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Promote the threshold family, not just the exact threshold:

- primary default: 10%;
- safer research variant: 5%;
- aggressive research-only variant: 15%;
- reject for now: 20%.

The next required check is capacity stress beyond the current 1,000,000 portfolio value. The current tradeability report only proves the candidates fit at the tested size; it does not prove they scale.
