# CN Stock Round329 Turnover-Low Vol-Target Sensitivity

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Objective

Round328 found the first useful recent research lead:

`turnover_rate_low + entry-cash tradeability handling + decision-aware volatility targeting`

Round329 tests whether the volatility-target overlay is a single lucky parameter point or a stable neighborhood.

## Inputs

- Base period return stream: `entry_cash_proxy_return`
- Decision date: `signal_date`
- Holding period: 20 trading days
- Annualization periods: `252 / 5`
- Walk-forward split: 3 years train / 1 year test / 1 year step
- Policy family: fixed volatility target only
- Targets: 4%, 5%, 6%, 7%, 8%, 10%
- Lookbacks: 42, 63, 84, 105, 126, 168 period-return observations

Output directory:

`data/reports/round329_24h_profit_sprint_turnover_low_vol_target_sensitivity_20260627`

## Walk-Forward Sensitivity

Average OOS overlap-adjusted Sharpe was broad, not a single isolated spike:

| Target | lb42 | lb63 | lb84 | lb105 | lb126 | lb168 |
|---:|---:|---:|---:|---:|---:|---:|
| 4% | 0.324 | 0.354 | 0.335 | 0.368 | 0.380 | 0.381 |
| 5% | 0.347 | 0.377 | 0.362 | 0.373 | 0.377 | 0.374 |
| 6% | 0.368 | 0.378 | 0.362 | 0.368 | 0.364 | 0.368 |
| 7% | 0.379 | 0.379 | 0.366 | 0.371 | 0.361 | 0.367 |
| 8% | 0.376 | 0.376 | 0.364 | 0.370 | 0.362 | 0.365 |
| 10% | 0.369 | 0.372 | 0.365 | 0.368 | 0.365 | 0.365 |

Top fixed policies by OOS overlap-adjusted Sharpe:

| Policy | Avg Test Ann | Avg Test Overlap Sharpe | Worst Test DD | Strict Pass |
|---|---:|---:|---:|---:|
| `vol_target_4_lb168` | +4.73% | 0.381 | -19.97% | 85.71% |
| `vol_target_4_lb126` | +4.50% | 0.380 | -19.18% | 71.43% |
| `vol_target_7_lb42` | +4.81% | 0.379 | -19.97% | 85.71% |
| `vol_target_7_lb63` | +4.80% | 0.379 | -19.97% | 85.71% |
| `vol_target_6_lb63` | +4.75% | 0.378 | -19.98% | 71.43% |

## Train-Selected Parameter Warning

Rolling train-selected parameter choice performed worse than using a fixed simple policy:

- selected average test annualized return: +3.75%
- selected average test overlap-adjusted Sharpe: 0.314
- positive test rate: 71.43%
- strict pass rate: 57.14%
- worst OOS drawdown: -18.42%

The worst selected fold was 2018:

- selected policy: `vol_target_4_lb84`
- test annualized return: -13.01%
- test overlap-adjusted Sharpe: -2.032
- test max drawdown: -18.42%

This is direct evidence against continuing to tune the volatility overlay by walk-forward train winner.

## Full-Sample Fixed-Policy Check

Full-sample fixed-policy results are diagnostic only, not promotion evidence.

| Policy | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---:|---:|---:|---:|---:|---:|
| `vol_target_4_lb84` | +139.45% | +5.42% | 0.929 | 0.489 | -26.26% | 79.28% |
| `vol_target_5_lb84` | +145.41% | +5.58% | 0.904 | 0.483 | -26.95% | 85.58% |
| `vol_target_6_lb84` | +147.58% | +5.63% | 0.878 | 0.475 | -26.87% | 90.50% |
| `vol_target_5_lb105` | +136.78% | +5.35% | 0.866 | 0.459 | -26.92% | 84.52% |
| `vol_target_7_lb84` | +142.69% | +5.50% | 0.838 | 0.456 | -26.80% | 93.24% |

## Decision

Continue this line, but freeze simple candidates instead of tuning.

Preferred candidates for the next robustness block:

- `vol_target_5_lb84`
- `vol_target_6_lb84`
- `vol_target_7_lb63`
- `vol_target_4_lb168`
- benchmark: `entry_cash_no_overlay`

Promotion stance:

- Simulation-ready: no
- Paper-ready: no

Reason:

- Dynamic parameter selection is unstable.
- Full-sample diagnostics remain multiple-testing exposed.
- The period-return stream is not yet a full daily mark-to-market engine.
- The 2026 window must remain a final holdout rather than a tuning set.
