# CN Stock Round335 - Calendar-Corrected Cash Exclusion + Vol Target

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Why This Round Exists

Round334 combined the `cash_low_turnover_f_bottom20` exclusion with fixed volatility-target overlays, but its overlay inputs dropped zero-return exit dates. That preserved total return but annualized the same PnL over 690 event rows instead of the full 834 exit-date calendar used by Round333.

Round335 corrects that by:

- using Round322 as the full exit-date / `signal_date` / `entry_date` calendar;
- attaching Round333 filter returns by exit date;
- keeping zero-return dates;
- applying overlay exposure on `entry_date`, based only on previously closed returns.

Output:

`data/reports/round335_24h_profit_sprint_turnover_low_cash_exclusion_voltarget_calendar_corrected_20260627`

2026 final holdout remains unused.

## Full-Sample Results

2015-2025, Top50, hold20, rebalance5, cost5 bps.

| Filter | Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cash_low_turnover_f_bottom20` | `vol_target_5_lb84` | +137.10% | +5.36% | 0.984 | 0.533 | -21.98% | 90.35% |
| `cash_low_turnover_f_bottom20` | `vol_target_6_lb84` | +134.08% | +5.27% | 0.938 | 0.512 | -21.96% | 94.00% |
| `entry_cash_no_extra_filter` | `vol_target_5_lb84` | +141.71% | +5.48% | 0.891 | 0.478 | -26.92% | 85.50% |
| `entry_cash_no_extra_filter` | `vol_target_6_lb84` | +144.69% | +5.56% | 0.869 | 0.471 | -26.84% | 90.40% |
| `cash_low_turnover_f_bottom20` | `vol_target_7_lb63` | +119.80% | +4.87% | 0.851 | 0.461 | -22.84% | 95.93% |

Key correction versus Round334:

- The corrected annualized return for `cash_low_turnover_f_bottom20 + vol_target_5_lb84` is +5.36%, not +6.18%.
- The corrected event count is 834, not 690.
- Total return remains comparable, but risk metrics are now on the same calendar as Round333.

## Cross-Split Robustness

Aggregated over train/test split schemes 2/1, 3/1, 4/1, and 5/1.

| Filter | Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cash_low_turnover_f_bottom20` | `vol_target_4_lb168` | +5.84% | +3.87% | 0.660 | 0.332 | -16.13% | 74.32% |
| `cash_low_turnover_f_bottom20` | `vol_target_7_lb63` | +5.80% | +3.86% | 0.655 | 0.328 | -16.13% | 74.32% |
| `cash_low_turnover_f_bottom20` | `no_overlay` | +5.76% | +3.81% | 0.650 | 0.322 | -16.13% | 74.32% |
| `cash_low_turnover_f_bottom20` | `vol_target_6_lb84` | +5.68% | +3.73% | 0.646 | 0.316 | -16.13% | 74.32% |
| `cash_low_turnover_f_bottom20` | `vol_target_5_lb84` | +5.53% | +3.60% | 0.639 | 0.310 | -16.13% | 74.32% |

## Decision

The useful part is not the overlay. The useful part is the cash exclusion:

`turnover_rate_low_top50_hold20_reb5_cost5 + entry_cash + cash_low_turnover_f_bottom20`

The fixed volatility-target wrapper can remain as a secondary wrapper candidate, but it should not be treated as the alpha source. After calendar correction, the most robust wrapper is `vol_target_4_lb168`, while `vol_target_5_lb84` gives the best full-sample Sharpe.

## Next Search Direction

Stop spending more budget on volatility-target micro-tuning. Continue with:

1. repair filters based on trade-level failure attribution;
2. public technical factors with known priors, especially low-volatility, trend persistence, breakout failure, RSRS, and smart-money style volume-price behavior;
3. strict validation with full calendar, entry-date decisions, costs, and 2026 holdout untouched.
