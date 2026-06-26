# CN Stock Round345 - Candidate External Regime Comparison

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round345 checks whether the Round344 external ETF regime overlay is specific to the primary candidate or useful across the current candidate set.

Candidates:

- safer benchmark: `cash_low_turnover_f_bottom20 + vol_target_5_lb84`;
- primary high-return candidate: `replace_drop_turnover_f_low10 + vol_target_6_lb84`;
- aggressive candidate: `replace_drop_turnover_f_low20_or_pb_high20 + vol_target_5_lb84`.

Regime policies:

- `baseline`;
- `zz500_mom120_neg_half`;
- `both_mom120_neg_cash`.

Output:

`data/reports/round345_24h_profit_sprint_candidate_external_regime_comparison_20260627`

2026 final holdout remains unused.

## Full-Sample Result

| Candidate | Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Safer cash | `baseline` | +137.10% | +5.36% | 0.984 | 0.533 | -21.98% |
| Safer cash | `zz500_mom120_neg_half` | +114.76% | +4.73% | 0.996 | 0.534 | -14.94% |
| Safer cash | `both_mom120_neg_cash` | +96.64% | +4.17% | 0.902 | 0.489 | -12.79% |
| Primary low10 | `baseline` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% |
| Primary low10 | `zz500_mom120_neg_half` | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% |
| Primary low10 | `both_mom120_neg_cash` | +123.63% | +4.98% | 0.918 | 0.497 | -14.48% |
| Aggressive low20/PB | `baseline` | +168.73% | +6.16% | 0.953 | 0.514 | -31.83% |
| Aggressive low20/PB | `zz500_mom120_neg_half` | +143.22% | +5.52% | 1.006 | 0.538 | -22.89% |
| Aggressive low20/PB | `both_mom120_neg_cash` | +118.43% | +4.83% | 0.915 | 0.494 | -16.71% |

## 2017-2018 Stress Period

| Candidate | Policy | 2017-2018 Total | 2017-2018 Ann. | 2017-2018 DD |
|---|---|---:|---:|---:|
| Safer cash | `baseline` | -18.35% | -5.03% | -21.98% |
| Safer cash | `zz500_mom120_neg_half` | -12.61% | -3.37% | -14.94% |
| Safer cash | `both_mom120_neg_cash` | -7.48% | -1.96% | -10.88% |
| Primary low10 | `baseline` | -24.36% | -6.86% | -28.88% |
| Primary low10 | `zz500_mom120_neg_half` | -17.66% | -4.83% | -20.38% |
| Primary low10 | `both_mom120_neg_cash` | -11.35% | -3.02% | -14.48% |
| Aggressive low20/PB | `baseline` | -26.65% | -7.58% | -31.83% |
| Aggressive low20/PB | `zz500_mom120_neg_half` | -19.81% | -5.46% | -22.89% |
| Aggressive low20/PB | `both_mom120_neg_cash` | -12.83% | -3.43% | -16.71% |

## Cross-Split Robustness

Aggregated across 30 one-year test folds from train/test schemes 2/1, 3/1, 4/1, and 5/1.

| Candidate | Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---|---:|---:|---:|---:|---:|
| Safer cash | `baseline` | +6.21% | -8.43% | 0.807 | -19.04% | 90.00% |
| Safer cash | `zz500_mom120_neg_half` | +4.72% | -4.75% | 0.790 | -11.68% | 90.00% |
| Safer cash | `both_mom120_neg_cash` | +3.43% | -2.41% | 0.703 | -7.85% | 66.67% |
| Primary low10 | `baseline` | +7.86% | -10.66% | 0.845 | -24.00% | 90.00% |
| Primary low10 | `zz500_mom120_neg_half` | +6.05% | -6.22% | 0.824 | -14.87% | 90.00% |
| Primary low10 | `both_mom120_neg_cash` | +4.46% | -3.91% | 0.901 | -10.04% | 76.67% |
| Aggressive low20/PB | `baseline` | +8.43% | -10.14% | 0.935 | -24.65% | 76.67% |
| Aggressive low20/PB | `zz500_mom120_neg_half` | +6.70% | -5.88% | 0.950 | -15.36% | 90.00% |
| Aggressive low20/PB | `both_mom120_neg_cash` | +4.90% | -5.31% | 0.921 | -12.93% | 76.67% |

## Interpretation

`zz500_mom120_neg_half` is not a one-candidate accident. It improves drawdown and risk-adjusted metrics across safer, primary, and aggressive candidates.

The most important comparison:

- Primary baseline gives the best total return: +177.08%, annualized +6.35%, max DD -28.88%.
- Primary + `zz500_mom120_neg_half` gives better risk-adjusted behavior: Sharpe 1.001, overlap 0.536, max DD -20.38%, but total return falls to +147.29%.
- Aggressive + `zz500_mom120_neg_half` has the highest full-sample overlap Sharpe in this round: 0.538, but total return is lower than primary baseline and it is not clearly superior to the primary defensive variant.

## Decision

Keep three simulation candidates:

1. High-return default:
   `primary_low10_vol6 baseline`

2. Preferred defensive variant:
   `primary_low10_vol6 + zz500_mom120_neg_half`

3. Ultra-defensive reference:
   `safer_cash_bottom20_vol5 + zz500_mom120_neg_half`

Do not make the aggressive candidate the default. With the same external regime overlay, it no longer offers enough extra return to justify its higher complexity and prior drawdown risk.

Next audit should review Rounds343-345 together and formalize these three candidate tiers before further mining.
