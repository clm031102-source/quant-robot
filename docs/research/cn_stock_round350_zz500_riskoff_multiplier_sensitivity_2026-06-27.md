# CN Stock Round350 - ZZ500 Risk-Off Multiplier Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round350 tests whether the CSI500 risk-off exposure multiplier should be 0%, 25%, 50%, 75%, or 100%.

Base candidate:

`primary_low10_vol6`

Rule:

When `CN_ETF_XSHG_510500` 120-day momentum is negative before the strategy decision date, multiply exposure by the tested risk-off multiplier.

Output:

`data/reports/round350_24h_profit_sprint_zz500_riskoff_multiplier_sensitivity_20260627`

2026 final holdout remains unused.

## Full-Sample Result

| Risk-Off Multiplier | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Regime Exposure |
|---:|---:|---:|---:|---:|---:|---:|
| 0% | +119.16% | +4.86% | 0.930 | 0.505 | -13.88% | 57.31% |
| 25% | +133.01% | +5.24% | 0.984 | 0.529 | -15.78% | 67.99% |
| 50% | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% | 78.66% |
| 75% | +161.99% | +5.99% | 0.989 | 0.530 | -24.74% | 89.33% |
| 100% | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | 100.00% |

## Cross-Split Result

| Risk-Off Multiplier | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---:|---:|---:|---:|---:|---:|
| 0% | +4.28% | -3.92% | 0.903 | -8.11% | 80.00% |
| 25% | +5.16% | -3.93% | 0.867 | -9.93% | 90.00% |
| 50% | +6.05% | -6.22% | 0.824 | -14.87% | 90.00% |
| 75% | +6.95% | -8.46% | 0.828 | -19.55% | 90.00% |
| 100% | +7.86% | -10.66% | 0.845 | -24.00% | 90.00% |

## Interpretation

The 50% risk-off multiplier remains the cleanest defensive setting:

- highest full-sample overlap Sharpe;
- max drawdown near -20%;
- OOS strict pass remains 90%.

The 75% multiplier is a useful new balanced candidate:

- total return improves from +147.29% at 50% risk-off exposure to +161.99%;
- annualized return improves from +5.62% to +5.99%;
- drawdown stays materially better than baseline: -24.74% vs -28.88%;
- OOS strict pass remains 90%.

The 0% hard-cash setting is too defensive for the user's stated preference unless the simulation objective becomes drawdown minimization.

## Decision

Keep:

- `primary_high_return`: risk-off multiplier 100%;
- `primary_defensive_zz500`: risk-off multiplier 50%;
- add research candidate `primary_balanced_zz500_75`: risk-off multiplier 75%.

Next work:

- cost and beta quick-check for the 75% balanced candidate;
- only add it to the packaged shortlist if it stays stronger than the 50% defensive candidate on cost/beta robustness.
