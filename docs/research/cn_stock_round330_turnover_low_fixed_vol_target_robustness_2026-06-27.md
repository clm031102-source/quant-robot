# CN Stock Round330 Fixed Vol-Target Robustness

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Objective

Round329 showed that volatility targeting around the low-turnover lead is a broad plateau, but rolling train-selected parameters are unstable. Round330 freezes a small set of candidates and checks robustness across:

- different walk-forward train windows;
- full 2015-2025 long-cycle metrics;
- yearly breakdown;
- China-specific bad subperiods.

The 2026 window is intentionally not used. It remains sealed as final holdout.

## Inputs

- Base return: `entry_cash_proxy_return`
- Decision date: `signal_date`
- Date window used: 2015-02-09 to 2025-02-28 by return date
- Decision-date window used: 2015-01-09 to 2025-02-28
- Holding period: 20 trading days
- Annualization periods: `252 / 5`

Frozen policies:

- `entry_cash_no_overlay`
- `vol_target_4_lb168`
- `vol_target_5_lb84`
- `vol_target_6_lb84`
- `vol_target_7_lb63`

Output directory:

`data/reports/round330_24h_profit_sprint_turnover_low_fixed_vol_target_robustness_20260627`

## Full-Sample Diagnostics

These are long-cycle diagnostics, not promotion evidence.

| Policy | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Win Rate | Avg Exposure | Min Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vol_target_5_lb84` | +145.41% | +5.58% | 0.904 | 0.483 | -26.95% | 41.13% | 86.78% | 39.04% |
| `vol_target_6_lb84` | +147.58% | +5.63% | 0.878 | 0.475 | -26.87% | 41.13% | 92.33% | 46.50% |
| `vol_target_7_lb63` | +129.35% | +5.14% | 0.786 | 0.421 | -29.08% | 41.13% | 95.03% | 56.24% |
| `vol_target_4_lb168` | +102.40% | +4.35% | 0.729 | 0.386 | -29.71% | 41.13% | 77.93% | 27.57% |
| `entry_cash_no_overlay` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% | 41.13% | 100.00% | 100.00% |

## Cross-Split Robustness

Train/test splits checked: 2/1, 3/1, 4/1, 5/1 years.

| Policy | Mean OOS Ann | Min OOS Ann | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Mean Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `vol_target_4_lb168` | +6.02% | +3.77% | 0.573 | 0.259 | -19.97% | 90.18% |
| `vol_target_7_lb63` | +6.04% | +3.83% | 0.571 | 0.257 | -19.97% | 90.18% |
| `entry_cash_no_overlay` | +5.94% | +3.69% | 0.562 | 0.245 | -19.97% | 90.18% |
| `vol_target_6_lb84` | +5.87% | +3.63% | 0.559 | 0.242 | -19.98% | 74.32% |
| `vol_target_5_lb84` | +5.62% | +3.46% | 0.551 | 0.242 | -19.50% | 74.32% |

Cross-split result:

- `vol_target_5_lb84` and `vol_target_6_lb84` win full-sample return and overlap Sharpe.
- `vol_target_4_lb168` and `vol_target_7_lb63` are more robust across split choices.
- The no-overlay benchmark is still competitive out-of-sample, so the overlay adds risk control more clearly than it adds durable alpha.

## Year And Regime Risk

Negative years:

| Policy | Year | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| `entry_cash_no_overlay` | 2018 | -20.04% | -10.86% | -2.275 | -2.313 | -23.32% | 100.00% |
| `vol_target_6_lb84` | 2018 | -20.04% | -10.86% | -2.275 | -2.313 | -23.32% | 100.00% |
| `vol_target_7_lb63` | 2018 | -20.04% | -10.86% | -2.275 | -2.313 | -23.32% | 100.00% |
| `vol_target_5_lb84` | 2018 | -19.99% | -10.83% | -2.271 | -2.302 | -23.32% | 99.67% |
| `vol_target_4_lb168` | 2018 | -19.97% | -10.82% | -2.269 | -2.298 | -23.32% | 99.12% |

Worst subperiod:

| Subperiod | Annual | Overlap Sharpe | Max DD | Key Point |
|---|---:|---:|---:|---|
| 2017-2018 deleveraging | about -6.5% | about -1.07 to -1.15 | about -27% | all policies lose together |

Interpretation:

- The realized-return volatility target reacts too late in 2017-2018.
- Because exposure is driven only by already closed strategy period returns, it cannot protect against a market regime shift before the strategy has already been hit.
- The next improvement should be an ex-ante market-state gate using market momentum/drawdown known by decision date.

## Decision

Status:

- Simulation-ready: no
- Paper-ready: no
- Best research lead: still active

Candidate ranking after Round330:

1. Robustness candidate: `vol_target_4_lb168`
2. Return candidate: `vol_target_5_lb84`
3. Balanced candidate: `vol_target_7_lb63`
4. Benchmark: `entry_cash_no_overlay`

Next action:

Test a simple, fixed, decision-date market-state cap layered with volatility targeting. Do not tune low-turnover parameters further unless the market-state cap fails and a new orthogonal hypothesis is registered.
