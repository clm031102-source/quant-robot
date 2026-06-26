# CN Stock Round333 Turnover-Low Failure Attribution

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Objective

Rounds331-332 tested market-state caps. They improved drawdown but either capped too often or failed to beat the no-overlay benchmark in walk-forward. Round333 switches from broad market timing to failure attribution inside the current strongest stock-selection lead:

`turnover_rate_low_top50_hold20_reb5_cost5`

The test only studies entry-allowed trades. Trades blocked at entry are already cash in the `entry_cash_proxy_return` stream and should not be misread as the live loss source.

## Data

- Trade rows: 26,450
- Entry-allowed rows: 20,841
- Entry-blocked rows: 5,609
- Date window: 2015-2025
- 2026 final holdout: not used

Output directory:

`data/reports/round333_24h_profit_sprint_turnover_low_failure_attribution_20260627`

## Feature Attribution

Worst feature buckets in 2017-2018 among entry-allowed trades:

| Feature | Bucket | Trades | Weighted Return Sum | Avg Gross Return | Avg Value |
|---|---:|---:|---:|---:|---:|
| `ps_ttm` | top bucket | 969 | -0.1140 | -2.25% | 8.87 |
| `high_52w_proximity` | bucket 1 | 873 | -0.1123 | -2.47% | -0.324 |
| `turnover_rate_f` | bottom bucket | 1,107 | -0.1078 | -1.85% | 0.343 |
| `realized_vol_20` | bucket 1 | 811 | -0.0964 | -2.28% | 0.012 |
| `drawdown_60` | bucket 2 | 722 | -0.0960 | -2.56% | 0.100 |
| `pe_ttm` | top bucket | 742 | -0.0950 | -2.46% | 1032.60 |

The cleanest economic clue is `turnover_rate_f` bottom 20%:

- It is different from raw `turnover_rate_low`.
- It suggests the weakest live trades are not simply "low turnover"; they are names with very stale free-float turnover inside a low-turnover selected basket.
- This is a plausible value-trap or dead-liquidity condition.

## Conservative Cash-Exclusion Diagnostics

These diagnostics do not replace excluded names. Excluded entry-allowed trades are sent to cash.

| Filter | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Cashed Trades |
|---|---:|---:|---:|---:|---:|---:|
| `cash_low_turnover_f_bottom20` | +107.79% | +4.52% | 0.750 | 0.414 | -28.01% | 4,091 |
| `cash_high_ps_or_low_turnover_f` | +90.13% | +3.96% | 0.777 | 0.432 | -19.45% | 6,962 |
| `cash_high_pb_or_low_turnover_f` | +80.63% | +3.64% | 0.721 | 0.401 | -22.45% | 7,307 |
| `cash_low_volume_ratio_bottom20` | +93.07% | +4.06% | 0.697 | 0.382 | -28.00% | 3,863 |
| `entry_cash_no_extra_filter` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% | 0 |

The best balanced rule is:

`cash_low_turnover_f_bottom20`

It preserves total and annualized return while materially improving Sharpe, overlap Sharpe, and drawdown.

## Subperiod Check

`cash_low_turnover_f_bottom20` versus no extra filter:

| Subperiod | No Filter Ann | Filter Ann | No Filter DD | Filter DD | Comment |
|---|---:|---:|---:|---:|---|
| 2015-2016 | +7.51% | +7.24% | -29.50% | -24.02% | slightly lower return, better drawdown |
| 2017-2018 | -6.48% | -5.03% | -26.80% | -21.96% | loss reduced |
| 2019-2020 | +9.15% | +8.25% | -14.71% | -11.27% | return lower, risk lower |
| 2021-2022 | +6.88% | +7.27% | -12.00% | -9.81% | return and risk both improve |
| 2023-2025 | +9.40% | +8.20% | -8.34% | -7.25% | return lower, drawdown lower |

## Cross-Split OOS Check

Across 2/1, 3/1, 4/1, and 5/1 year train/test splits:

| Filter | Mean OOS Ann | Min OOS Ann | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Mean Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `cash_low_turnover_f_bottom20` | +5.94% | +4.23% | 0.655 | 0.352 | -16.75% | 90.18% |
| `cash_high_pb_or_low_turnover_f` | +4.65% | +3.21% | 0.638 | 0.323 | -14.29% | 74.32% |
| `cash_high_ps_or_low_turnover_f` | +4.47% | +3.12% | 0.593 | 0.300 | -13.00% | 74.32% |
| `entry_cash_no_extra_filter` | +6.18% | +4.26% | 0.561 | 0.273 | -20.59% | 90.18% |

## Decision

Status:

- Simulation-ready: no
- Paper-ready: no
- Best current repair candidate: `turnover_rate_low + entry-cash + cash_low_turnover_f_bottom20`

Why it is useful:

- Fixed rule, not rolling optimized.
- Explains a real failure pocket in 2017-2018.
- Improves OOS overlap-adjusted Sharpe and worst OOS drawdown.
- Does not rely on broad market timing.
- Does not rely on replacing excluded names with potentially overfit alternatives.

Next action:

Run the exact portfolio diagnostic for this candidate as a formal factor/portfolio configuration, then compare it against:

- `entry_cash_no_extra_filter`;
- `vol_target_5_lb84`;
- `vol_target_4_lb168`;
- possible combination with the low-turnover-f exclusion only if the fixed cash-exclusion result remains strong.
