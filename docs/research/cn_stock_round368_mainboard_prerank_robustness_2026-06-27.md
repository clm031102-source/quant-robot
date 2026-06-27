# CN Stock Round368 - Mainboard Pre-Rank Robustness and Vol-Target Check

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Why This Round

Round367 showed a higher-return but higher-drawdown mainboard pre-rank variant. Round368 tests whether that lead is robust enough to keep pursuing.

Checks:

1. block-dependence audit on entry-cash period returns;
2. fixed OOS split without parameter selection;
3. calendar-aware vol-target wrapper sensitivity.

## Outputs

Block audit:

`data/reports/round368_24h_profit_sprint_mainboard_prerank_block_audit_20260627`

OOS split:

`data/reports/round368_24h_profit_sprint_mainboard_prerank_oos_split_20260627`

Vol-target overlay:

`data/reports/round368_24h_profit_sprint_mainboard_prerank_voltarget_overlay_20260627`

Vol-target sensitivity:

`data/reports/round368_24h_profit_sprint_mainboard_prerank_voltarget_sensitivity_20260627`

Vol-target block audit:

`data/reports/round368_24h_profit_sprint_mainboard_prerank_voltarget_block_audit_20260627`

## Block Dependence

Entry-cash returns:

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Blockers |
|---|---:|---:|---:|---:|---:|---|
| `replace_drop_turnover_f_low10_entry_cash_after` | +144.38% | 5.33% | 0.738 | 0.407 | -36.99% | none |
| `replace_drop_turnover_f_low10_mainboard_prerank` | +180.65% | 6.86% | 0.704 | 0.384 | -48.95% | best-month concentration |
| `turnover_low_top50_entry_cash_after` | +107.64% | 4.51% | 0.644 | 0.355 | -35.63% | best-month concentration |

The mainboard pre-rank variant relies too much on early 2015 return blocks before risk wrapping.

## Fixed OOS Split

The split uses already-defined candidates only. There is no parameter selection inside the split.

| Candidate | Folds | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `replace_drop_turnover_f_low10_mainboard_prerank` | 26 | 10.02% | -18.11% | 0.858 | -28.12% | 88.46% |
| `replace_drop_turnover_f_low10_entry_cash_after` | 26 | 8.06% | -11.25% | 0.707 | -23.33% | 88.46% |
| `turnover_low_top50_entry_cash_after` | 26 | 5.94% | -11.17% | 0.521 | -20.59% | 88.46% |

The mainboard variant has stronger average OOS return, but its left tail is worse.

## Vol-Target Sensitivity

Calendar-aware vol target uses closed prior returns and `lookback_events=84`.

| Source | Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---|---:|---:|---:|---:|---:|---:|
| `drop_low10` | `vol_target_4_lb84` | +144.57% | 5.33% | 0.884 | 0.476 | -29.27% | 77.95% |
| `drop_low10` | `vol_target_5_lb84` | +155.75% | 5.60% | 0.878 | 0.476 | -30.49% | 84.13% |
| `drop_low10` | `vol_target_6_lb84` | +165.89% | 5.84% | 0.881 | 0.481 | -30.48% | 89.22% |
| `mainboard_prerank` | `vol_target_4_lb84` | +171.37% | 6.63% | 0.927 | 0.455 | -36.71% | 69.47% |
| `mainboard_prerank` | `vol_target_5_lb84` | +180.97% | 6.87% | 0.902 | 0.452 | -39.07% | 77.03% |
| `mainboard_prerank` | `vol_target_6_lb84` | +191.19% | 7.11% | 0.886 | 0.451 | -40.54% | 83.11% |
| `mainboard_prerank` | `vol_target_8_lb84` | +219.79% | 7.76% | 0.897 | 0.465 | -41.73% | 90.41% |

The mainboard variant remains above the 30% drawdown tolerance even at 4% target volatility.

## Decision

Do not add `replace_drop_turnover_f_low10_mainboard_prerank` to the simulation shortlist.

Keep the current lower-risk primary line:

`replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

For a stricter drawdown lane, `drop_low10 + vol_target_4_lb84` is a useful reference because it keeps max drawdown just under 30%, but it does not beat the existing ZZ500 defensive shortlist on risk-adjusted evidence.

The board-permission pre-rank idea is useful as an operational control, not yet as a better alpha candidate.
