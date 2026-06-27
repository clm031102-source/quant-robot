# CN Stock Round387 - Self-Risk Overlay On Dragon-Hot Lane

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round387 tested whether the stronger `dragon_hot_100` event lane can be improved with repeatable self-risk budget rules.

The overlay decision uses only strategy returns already closed before each event date:

- prior 21-event return sum;
- prior 42-event return sum;
- prior strategy drawdown.

It does not use the current event return to decide current exposure.

## New Tooling

- `src/quant_robot/ops/shortlist_self_risk_overlay.py`
- `scripts/run_shortlist_self_risk_overlay.py`
- `tests/unit/test_shortlist_self_risk_overlay.py`
- `src/quant_robot/ops/shortlist_event_beta_audit.py`
- `scripts/run_shortlist_event_beta_audit.py`
- `tests/unit/test_shortlist_event_beta_audit.py`

The self-risk tool applies the same policy suite to any frozen event-return source. The event beta tool audits any frozen event-return source against benchmark event returns.

## Outputs

- Projection: `data/reports/round387_24h_profit_sprint_self_risk_overlay_on_dragon_hot_20260627`
- OOS split: `data/reports/round387_24h_profit_sprint_self_risk_overlay_on_dragon_hot_oos_20260627`
- Block audit: `data/reports/round387_24h_profit_sprint_self_risk_overlay_on_dragon_hot_block_audit_20260627`
- Beta audit: `data/reports/round387_24h_profit_sprint_self_risk_overlay_on_dragon_hot_beta_audit_20260627`

## Full-Sample Result

| Candidate | Policy | Total | Ann. | Sharpe | Overlap | Max DD | Avg Exposure | Guard Share |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `dragon_hot_100_self_roll21_sum_neg_half` | Half exposure when prior 21-event sum is negative | +193.10% | 6.71% | 1.173 | 0.617 | -15.46% | 80.64% | 38.73% |
| `primary_100_self_roll21_sum_neg_half` | Same rule on primary lane | +190.58% | 6.66% | 1.146 | 0.601 | -15.64% | 80.58% | 38.85% |
| `dragon_hot_100_self_roll21_sum_m2_cash` | Cash when prior 21-event sum < -2% | +184.90% | 6.53% | 1.137 | 0.599 | -14.22% | 71.82% | 28.18% |
| `dragon_hot_100` | No extra self-risk overlay | +181.20% | 6.45% | 0.987 | 0.532 | -28.57% | 100.00% | 0.00% |
| `dragon_hot_100_self_roll42_sum_m3_half` | Half exposure when prior 42-event sum < -3% | +179.39% | 6.41% | 1.061 | 0.570 | -19.66% | 88.37% | 23.26% |
| `primary_100` | No extra self-risk overlay | +177.08% | 6.35% | 0.960 | 0.517 | -28.88% | 100.00% | 0.00% |

The main useful result is `dragon_hot_100_self_roll21_sum_neg_half`: unlike most defensive overlays, it improved both full-sample return and drawdown.

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `dragon_hot_100` | 8.02% | 0.869 | -23.68% | 90.00% |
| `dragon_hot_100_self_roll42_sum_m3_half` | 7.77% | 0.854 | -15.10% | 90.00% |
| `dragon_hot_100_self_roll21_sum_neg_half` | 7.20% | 0.854 | -12.75% | 90.00% |
| `dragon_hot_100_self_combo_roll21_neg_or_dd10_half` | 6.52% | 0.879 | -12.59% | 90.00% |
| `primary_100` | 7.86% | 0.845 | -24.00% | 90.00% |
| `primary_100_self_roll21_sum_neg_half` | 7.10% | 0.834 | -12.93% | 90.00% |

OOS does not confirm that `roll21_sum_neg_half` has higher return than baseline. It does confirm that the drawdown reduction is large and repeatable.

## Block Audit

`dragon_hot_100_self_roll21_sum_neg_half` passed the block audit:

- full-sample total return: +193.10%;
- annualized return: 6.71%;
- max drawdown: -15.46%;
- leave-one-year minimum annualized return: 4.42%;
- leave-one-year minimum overlap Sharpe: 0.543;
- best three-month log contribution share: 42.99%;
- worst removed year: 2015.

The 2015 dependence is still visible, but it is not worse than the existing primary family and the leave-one-year return stays positive.

## Beta Audit

Against ZZ500 event returns:

| Candidate | Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|---:|
| `dragon_hot_100_self_roll21_sum_neg_half` | 0.0333 | 0.2348 | 6.68% | 0.979 | -9.49% |
| `dragon_hot_100` | 0.0396 | 0.2496 | 6.41% | 0.843 | -13.28% |
| `primary_100` | 0.0403 | 0.2508 | 6.32% | 0.826 | -13.40% |

The self-risk rule reduces benchmark beta and improves hedged drawdown/overlap. It does not look like a hidden increase in index exposure.

## Decision

Add a new simulation observation lane:

`primary_high_return_dragon_hot_chase_self_risk_roll21`

Formula:

`primary_low10_vol6 + dragon_hot_chase_20d cash filter + ZZ500 risk-off multiplier 1.00 + self-risk roll21_sum_neg_half`

Status:

`simulation_shortlist_risk_budget_observation`

Why it is not the default:

- full-sample total return, Sharpe, overlap, and drawdown are all better than `dragon_hot_100`;
- OOS return is lower than `dragon_hot_100`, so this is a risk-budget candidate rather than a pure return upgrade;
- it should be tested in simulation as an alternate risk profile, not silently replace the high-return lane.

Reject as default:

- `roll21_sum_m2_cash`, because it cuts exposure too aggressively and weakens OOS pass rate;
- `combo_roll21_neg_or_dd10_half`, because it is excellent for drawdown but gives up too much return;
- `current_dd_15_cash`, because it is too late and too blunt for the current return objective.

## Process Lesson

The best current improvement came from portfolio/risk-budget logic, not another stock-selection factor. For the 24h sprint, every high-return candidate should now be tested with the same reusable self-risk suite before simulation handoff.
