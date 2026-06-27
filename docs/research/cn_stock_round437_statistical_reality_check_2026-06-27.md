# CN Stock Round437 Statistical Reality Check

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round437 applied a strict statistical reality check to the current delayed-exit simulation pack before any further promotion language.

Candidates checked:

- delayed-exit baseline at 10, 20, and 30 bps;
- delayed-exit plus `zero_quarter_end5` at 10, 20, and 30 bps.

This round answers a narrow question: does the current pack clear multiple-testing-aware statistical promotion gates, or should it remain a simulation-observation pack?

## Method

Inputs:

- `data/reports/round437_24h_profit_sprint_statistical_reality_20260627/stat_reality_experiments.csv`
- `data/reports/round437_24h_profit_sprint_statistical_reality_20260627/purged_cpcv_return_summary.csv`
- `data/reports/round437_24h_profit_sprint_statistical_reality_check_20260627/factor_statistical_reality_check.json`

Controls:

- metric: `overlap_autocorr_adjusted_sharpe`;
- effective sample policy: `period_count / 4`, minimum 30, to account for overlapping 20d holdings;
- hypotheses: 6;
- multiple testing: Benjamini-Hochberg FDR;
- split stability: 6 groups, choose 2 test groups, 15 purged/CPCV-style splits;
- purge observations: 4;
- embargo observations: 4;
- 2026 final holdout excluded.

## FDR Reality Check

All six lanes pass the deflated-Sharpe probability check, but none survive the 5% FDR gate. The top adjusted q-value is about 0.064, so this is close but still below the project's promotion standard.

| Rank | Case | Overlap Sharpe | p-value | FDR q | FDR Significant | Statistical Candidate |
|---:|---|---:|---:|---:|---|---|
| 1 | `cost10_zero_qe` | 0.546 | 0.02066 | 0.06400 | no | no |
| 2 | `cost20_zero_qe` | 0.506 | 0.03192 | 0.06400 | no | no |
| 3 | `cost10_base` | 0.496 | 0.03553 | 0.06400 | no | no |
| 4 | `cost30_zero_qe` | 0.465 | 0.04901 | 0.06400 | no | no |
| 5 | `cost20_base` | 0.456 | 0.05333 | 0.06400 | no | no |
| 6 | `cost30_base` | 0.416 | 0.07777 | 0.07777 | no | no |

Interpretation: the current pack is good enough to continue simulation preparation, but not good enough to describe as a statistically final alpha discovery.

## Purged Split Stability

The purged split check favors the quarter-end defensive overlay on robustness, even though baseline keeps slightly higher mean annualized return.

| Candidate | Splits | Mean Ann. | Min Ann. | Mean Overlap | Min Overlap | Worst DD | Positive Ann. | DD <= 30% Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `cost10_zero_qe` | 15 | 6.468% | -0.346% | 0.573 | -0.040 | -30.40% | 93.33% | 93.33% |
| `cost20_zero_qe` | 15 | 5.951% | -0.653% | 0.528 | -0.085 | -31.36% | 93.33% | 93.33% |
| `cost10_base` | 15 | 6.732% | -0.212% | 0.519 | -0.019 | -32.87% | 93.33% | 86.67% |
| `cost30_zero_qe` | 15 | 5.345% | -1.032% | 0.481 | -0.142 | -31.90% | 93.33% | 86.67% |
| `cost20_base` | 15 | 6.124% | -0.544% | 0.475 | -0.065 | -33.89% | 93.33% | 80.00% |
| `cost30_base` | 15 | 5.475% | -0.948% | 0.429 | -0.122 | -34.46% | 93.33% | 80.00% |

## Decision

No lane is promoted as a statistically final alpha in Round437.

Use the pack as follows:

- keep `cost10_base` as the default return-seeking simulation lane because it has the highest full-sample annualized return among the core lanes;
- keep `cost10_zero_qe` as the best defensive simulation lane because it has the highest overlap Sharpe, lower full-sample drawdown, lower best-month concentration, and the best purged split drawdown pass rate;
- keep 20 bps and 30 bps lanes as cost-stress monitoring lanes;
- do not open the 2026 final holdout yet.

Blocked follow-ups:

- do not call a deflated-Sharpe pass alone a promotable result;
- do not tune quarter-end thresholds after seeing this result unless a new hypothesis is pre-registered and counted;
- do not describe `zero_quarter_end5` as independent alpha;
- do not move to broker, account, order, or live-trading actions.

Next useful work:

- continue mining independent, entry-known factor families;
- improve capacity/cost modeling before simulation;
- add stricter White-Reality-Check-style bootstrap when time permits;
- preserve the three-round audit cadence so weak families are rotated quickly.
