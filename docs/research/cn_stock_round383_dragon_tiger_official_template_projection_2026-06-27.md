# CN Stock Round383 - Dragon-Tiger Official Template Projection

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round382 showed that naive Dragon-Tiger cash filters improved the low-turnover replacement basket, but failed calendar parity because the naive exit-date aggregation produced 872 dates versus the frozen official 834-date template.

Round383 fixes that failure mode by projecting flagged trade contributions onto the frozen official Round339 template.

Reusable code added:

- `src/quant_robot/ops/shortlist_official_template_cash_filter.py`
- `scripts/run_shortlist_official_template_cash_filter.py`
- `tests/unit/test_shortlist_official_template_cash_filter.py`

## Output

- Official-template projection: `data/reports/round383_24h_profit_sprint_dragon_tiger_official_template_projection_20260627`
- OOS split: `data/reports/round383_24h_profit_sprint_dragon_tiger_official_template_oos_20260627`
- Block audit: `data/reports/round383_24h_profit_sprint_dragon_tiger_official_template_block_audit_20260627`

## Full-Sample Official Template Results

All candidates use the official 834-date Round339 template.

| Candidate | Total | Ann. | Sharpe | Overlap | Max DD | Unmatched Abs Contribution |
|---|---:|---:|---:|---:|---:|---:|
| `official_base` | +150.65% | 5.71% | 0.779 | 0.428 | -35.29% | n/a |
| `cash_dragon_hot_chase_20d` | +159.79% | 5.94% | 0.826 | 0.454 | -32.87% | 0.00033 |
| `cash_dragon_net_buy_20d` | +158.90% | 5.92% | 0.824 | 0.452 | -32.99% | 0.00033 |
| `cash_dragon_hot_sell_60d` | +157.14% | 5.87% | 0.830 | 0.456 | -30.82% | 0.00369 |

The previous calendar-parity blocker is materially reduced. `cash_dragon_hot_chase_20d` has only 3 unmatched flagged trades and 0.00033 unmatched absolute contribution.

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `cash_dragon_hot_chase_20d` | 9.06% | 0.898 | -23.68% | 90.00% |
| `cash_dragon_net_buy_20d` | 9.00% | 0.887 | -23.56% | 90.00% |
| `official_base` | 8.90% | 0.875 | -24.00% | 90.00% |
| `cash_dragon_hot_sell_60d` | 8.59% | 0.818 | -23.26% | 90.00% |

## Decision

Promote `cash_dragon_hot_chase_20d` from research lead to package-level comparison.

It is not yet a standalone simulation candidate. It must be tested after the existing `vol_target_6_lb84` and ZZ500 risk-off wrappers, because the current simulation shortlist is built on those wrappers rather than the unwrapped official base.
