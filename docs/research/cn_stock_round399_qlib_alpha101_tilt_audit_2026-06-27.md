# CN Stock Round399 - Qlib Alpha101 Tilt Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round399 audited the Round398 Qlib/Alpha101 selected-entry tilt against the existing `dragon_hot_100` high-return reference.

The two audited tilt lanes were:

- `qlib_top10_m150`: top 10% Qlib factor entries, 1.50x exposure.
- `qlib_top15_m150`: top 15% Qlib factor entries, 1.50x exposure.

## Outputs

- OOS split: `data/reports/round399_24h_profit_sprint_qlib_alpha101_tilt_oos_20260627`
- Block audit: `data/reports/round399_24h_profit_sprint_qlib_alpha101_tilt_block_audit_20260627`
- Beta audit: `data/reports/round399_24h_profit_sprint_qlib_alpha101_tilt_beta_audit_20260627`
- Capacity upper bound: `data/reports/round399_24h_profit_sprint_qlib_alpha101_tilt_capacity_upper_bound_20260627`

## Full Sample And Block Audit

| Candidate | Total | Ann. | Sharpe | Overlap | Max DD | Leave-One-Year Min Ann. | Blockers |
|---|---:|---:|---:|---:|---:|---:|---|
| `qlib_top15_m150` | 1.9530 | 6.76% | 0.962 | 0.518 | -30.52% | 4.09% | none |
| `qlib_top10_m150` | 1.9015 | 6.65% | 0.969 | 0.522 | -29.79% | 4.05% | none |
| `dragon_hot_100` | 1.8120 | 6.45% | 0.987 | 0.532 | -28.57% | 3.96% | none |

The tilt raises return but gives up some Sharpe/overlap and increases drawdown. The best practical trade-off is `qlib_top10_m150`.

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `qlib_top15_m150` | 8.48% | 0.853 | -25.55% | 90.0% |
| `qlib_top10_m150` | 8.38% | 0.861 | -24.98% | 90.0% |
| `dragon_hot_100` | 8.02% | 0.869 | -23.68% | 90.0% |

The OOS pattern confirms the same trade-off: higher return, slightly weaker risk shape.

## Beta Audit

| Candidate | Benchmark | Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---|---:|---:|---:|---:|---:|
| `qlib_top10_m150` | ZZ500 | 0.0416 | 0.2495 | 6.62% | 0.827 | -13.72% |
| `dragon_hot_100` | ZZ500 | 0.0396 | 0.2496 | 6.41% | 0.843 | -13.28% |
| `qlib_top10_m150` | HS300 | 0.0498 | 0.1996 | 6.87% | 0.704 | -30.41% |
| `dragon_hot_100` | HS300 | 0.0471 | 0.1970 | 6.65% | 0.713 | -29.20% |

The added return is not just a benchmark beta jump. R2 is effectively unchanged, although hedged overlap is weaker than the Dragon-Hot reference.

## Capacity And Cost Notes

The selected-trade source already stores `entry_cash_proxy_weighted_return = target_weight * net_return`, and `net_return = gross_return - cost_rate`. The tilt therefore scales a net, costed contribution.

A conservative upper-bound capacity stress scaled all low10 trades, not just the 10% tilt subset:

| AUM Multiplier | Max Participation | Breaches | Capacity Safe |
|---:|---:|---:|---|
| 1.5x | 0.192% | 0 | yes |
| 2x | 0.256% | 0 | yes |
| 5x | 0.640% | 0 | yes |
| 10x | 1.280% | 0 | yes |

Capacity is not the binding blocker at current research scale.

## Decision

Add `primary_high_return_dragon_hot_chase_qlib_top10_tilt_m150` as a simulation observation, not as the default.

Reason:

- It improves full-sample total return from 181.20% to 190.15%.
- It improves annualized return from 6.45% to 6.65%.
- It keeps full-sample max drawdown just under 30%.
- It has higher OOS annualized return than `dragon_hot_100`.
- It loses some Sharpe/overlap quality and has worse OOS drawdown, so it should be treated as the aggressive high-return lane.

Next step: test whether self-risk or ETF risk-budget variants can keep the added return while reducing the extra drawdown.
