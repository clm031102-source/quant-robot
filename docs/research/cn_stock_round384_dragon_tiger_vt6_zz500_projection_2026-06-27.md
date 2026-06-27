# CN Stock Round384 - Dragon-Tiger VT6 + ZZ500 Projection

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round383 validated the Dragon-Tiger hot-chase cash filter on the frozen official event calendar. Round384 tests whether that edge survives the actual simulation shortlist wrappers:

- `vol_target_6_lb84`;
- ZZ500 120-day momentum risk-off multipliers at 1.00, 0.75, and 0.50;
- current cost-rate event streams.

The vol-target reproduction check against Round339 passed:

| Check | Max Abs Return Diff | Max Abs Exposure Diff |
|---|---:|---:|
| Round339 `vol_target_6_lb84` reproduction | 9.98e-17 | 1.11e-16 |

## Output

- Projection: `data/reports/round384_24h_profit_sprint_dragon_tiger_vt6_zz500_projection_20260627`
- OOS split: `data/reports/round384_24h_profit_sprint_dragon_tiger_vt6_zz500_oos_20260627`
- Block audit: `data/reports/round384_24h_profit_sprint_dragon_tiger_vt6_zz500_block_audit_20260627`
- Beta audit: `data/reports/round384_24h_profit_sprint_dragon_tiger_vt6_zz500_beta_audit_20260627`

## Full-Sample Comparison

| Lane | Total | Ann. | Sharpe | Overlap | Max DD |
|---|---:|---:|---:|---:|---:|
| `dragon_hot_100` | +181.20% | 6.45% | 0.987 | 0.532 | -28.57% |
| `primary_100` | +177.08% | 6.35% | 0.960 | 0.517 | -28.88% |
| `dragon_hot_075` | +165.18% | 6.07% | 1.017 | 0.546 | -24.43% |
| `primary_075` | +161.99% | 5.99% | 0.989 | 0.530 | -24.74% |
| `dragon_hot_050` | +149.64% | 5.68% | 1.028 | 0.552 | -20.07% |
| `primary_050` | +147.29% | 5.62% | 1.001 | 0.536 | -20.38% |

## OOS Split

| Lane | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `dragon_hot_100` | 8.02% | 0.869 | -23.68% | 90.00% |
| `primary_100` | 7.86% | 0.845 | -24.00% | 90.00% |
| `dragon_hot_075` | 7.11% | 0.854 | -19.24% | 90.00% |
| `primary_075` | 6.95% | 0.828 | -19.55% | 90.00% |
| `dragon_hot_050` | 6.20% | 0.849 | -14.57% | 90.00% |
| `primary_050` | 6.05% | 0.824 | -14.87% | 90.00% |

## Beta Sanity Check

The Dragon-Tiger overlay does not materially increase benchmark dependence.

| Lane | Benchmark | Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---|---:|---:|---:|---:|---:|
| `dragon_hot_100` | ZZ500 | 0.0396 | 0.2496 | 6.41% | 0.843 | -13.28% |
| `primary_100` | ZZ500 | 0.0403 | 0.2508 | 6.32% | 0.826 | -13.40% |
| `dragon_hot_075` | ZZ500 | 0.0360 | 0.2475 | 6.04% | 0.897 | -12.12% |
| `primary_075` | ZZ500 | 0.0366 | 0.2484 | 5.96% | 0.876 | -12.37% |
| `dragon_hot_050` | ZZ500 | 0.0323 | 0.2336 | 5.65% | 0.913 | -12.25% |
| `primary_050` | ZZ500 | 0.0329 | 0.2341 | 5.59% | 0.890 | -12.50% |

## Decision

`dragon_hot_chase_20d` is the best usable increment found in this block.

Recommendation:

- keep the existing three primary lanes;
- add `dragon_hot_chase` as a simulation observation overlay, not as a replacement default yet;
- preferred new lane for the user's drawdown tolerance is `dragon_hot_100`, because it has the best return and still keeps max drawdown below 30%;
- conservative new lane is `dragon_hot_050`, because it improves overlap and drawdown versus `primary_050`.

Main caveat: the incremental annualized return is small, roughly +0.06 to +0.10 percentage points full-sample and +0.15 to +0.16 percentage points OOS. It is useful because it is consistent and calendar-safe, not because it is a large standalone alpha.
