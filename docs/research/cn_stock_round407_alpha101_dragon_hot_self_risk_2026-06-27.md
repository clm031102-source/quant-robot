# CN Stock Round407 - Alpha101 Dragon-Hot Self-Risk

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round406 found a high-return Alpha101 open-close tilt, but its max drawdown was close to the user's 30% tolerance. Round407 applied the existing PIT self-risk overlay suite to test whether the return could be preserved while reducing drawdown.

## Input Candidates

- `tilt_a101_open_100`
- `tilt_a101_open_075`
- `tilt_a101_vwap_100`
- `cash_a101_open_100`
- `cash_a101_open_075`

Output: `data/reports/round407_24h_profit_sprint_alpha101_dragon_hot_self_risk_20260627`

## Best Full-Sample Rows

| Candidate | Policy | Annualized | Overlap Sharpe | Max Drawdown | Avg Exposure | Guard Share |
|---|---|---:|---:|---:|---:|---:|
| `tilt_a101_vwap_100_self_roll21_sum_m2_cash` | cash when prior 21-event sum < -2% | 7.65% | 0.659 | -14.57% | 71.94% | 28.06% |
| `tilt_a101_open_100_self_roll21_sum_m2_cash` | cash when prior 21-event sum < -2% | 7.65% | 0.658 | -14.57% | 72.06% | 27.94% |
| `tilt_a101_open_100_self_roll21_sum_neg_half` | half when prior 21-event sum < 0 | 7.52% | 0.645 | -16.45% | 80.70% | 38.61% |
| `tilt_a101_vwap_100_self_roll21_sum_neg_half` | half when prior 21-event sum < 0 | 7.50% | 0.644 | -16.45% | 80.70% | 38.61% |
| `tilt_a101_open_100` | baseline | 7.21% | 0.558 | -29.84% | 100.00% | 0.00% |

## Decision

Advance both `m2_cash` and `neg_half` policies to Round408.

Do not trust the full-sample winner yet. The same `m2_cash` policy had previously shown full-sample strength but weaker OOS behavior on the Qlib branch.
