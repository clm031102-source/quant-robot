# CN Stock Round403 - Qlib Alpha101 Tilt ZZ500 Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round403 tested whether changing the ZZ500 risk-off multiplier gives a better risk-return profile for the Qlib tilt lane than self-risk overlays.

Output:

`data/reports/round403_24h_profit_sprint_qlib_alpha101_tilt_zz500_multiplier_sensitivity_20260627`

## Result

| Candidate | Risk-Off Mult. | Total | Ann. | Sharpe | Overlap | Max DD | Leave-One-Year Min Ann. |
|---|---:|---:|---:|---:|---:|---:|---:|
| `qlib_top15_m150` | 1.00 | 1.9530 | 6.76% | 0.962 | 0.518 | -30.52% | 4.09% |
| `qlib_top10_m150` | 1.00 | 1.9015 | 6.65% | 0.969 | 0.522 | -29.79% | 4.05% |
| `qlib_top15_m150` | 0.75 | 1.7755 | 6.36% | 0.991 | 0.531 | -26.10% | 3.70% |
| `qlib_top10_m150` | 0.75 | 1.7295 | 6.26% | 0.998 | 0.535 | -25.46% | 3.67% |
| `qlib_top15_m150` | 0.50 | 1.6035 | 5.95% | 1.000 | 0.536 | -21.43% | 3.30% |
| `qlib_top10_m150` | 0.50 | 1.5627 | 5.85% | 1.008 | 0.541 | -20.90% | 3.27% |

## Decision

Do not add a separate ZZ500 0.75/0.50 Qlib tilt lane.

The risk-off multiplier sensitivity gives the expected defensive trade-off, but it does not beat the self-risk route:

- lower drawdown;
- lower return;
- no stronger OOS or beta evidence than `qlib_top10_m150_self_roll21_sum_neg_half`.

Keep the current best Qlib risk-budget observation as:

`primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150_self_roll21`
