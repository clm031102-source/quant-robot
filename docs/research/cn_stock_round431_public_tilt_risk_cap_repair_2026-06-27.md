# CN Stock Round431 Public Tilt Risk Cap Repair

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round431 tests whether the remaining Round430 tail profile can be improved with entry-known risk caps on the public-factor tilt.

The profile showed public-tilted trades, higher `turnover_rate_f`, and higher `pb` had elevated extreme-trade risk. The repair is intentionally narrow: if a public-tilted trade breaches an entry-known threshold, reduce its tilt multiplier from 1.50x to 1.00x.

## Reusable Code Added

`scripts/run_simulation_shortlist_cohort_entry_timed.py` and `src/quant_robot/ops/simulation_shortlist_cohort_entry_timed.py` now support:

- `public_factor_tilt_risk_cap_column`
- `public_factor_tilt_risk_cap_operator`
- `public_factor_tilt_risk_cap_value`
- `public_factor_tilt_risk_cap_multiplier`

This lets future runs test entry-known public-tilt risk budgets without ad hoc trade edits.

## Candidates

All candidates use the Round430 roundtrip execution-stress return stream and 1.50x baseline public tilt unless capped.

| Candidate | Risk Cap | Capped Trades | Annualized | Total Return | Overlap Sharpe | Max DD |
|---|---|---:|---:|---:|---:|---:|
| `roundtrip_m150` | none | 0 | 5.832% | +166.65% | 0.486 | -25.98% |
| `cap_turnoverf_gt3` | `turnover_rate_f > 3.0` | 271 | 5.666% | +159.49% | 0.482 | -25.95% |
| `cap_turnoverf_gt4` | `turnover_rate_f > 4.0` | 148 | 5.772% | +164.01% | 0.486 | -25.70% |
| `cap_pb_gt3p6` | `pb > 3.6` | 419 | 5.727% | +162.09% | 0.485 | -25.61% |

## OOS And Beta

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass | Hedged Ann. | Hedged Overlap | Hedged Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| `roundtrip_m150` | 8.369% | 0.873 | -19.46% | 90.00% | 6.264% | 0.778 | -13.55% |
| `cap_turnoverf_gt4` | 8.340% | 0.872 | -19.46% | 90.00% | 6.200% | 0.768 | -13.85% |
| `cap_pb_gt3p6` | 8.244% | 0.866 | -19.33% | 90.00% | 6.148% | 0.771 | -13.80% |

## Extreme Profile

The caps reduce extreme contribution slightly but do not change the extreme trade count:

| Candidate | Extreme Count | Extreme Contribution | Total Contribution |
|---|---:|---:|---:|
| `roundtrip_m150` | 102 | +36.79 pp | +101.92 pp |
| `cap_turnoverf_gt4` | 102 | +36.21 pp | +100.87 pp |
| `cap_pb_gt3p6` | 102 | +35.98 pp | +100.10 pp |

## Decision

Do not upgrade the public-tilt risk caps.

Reason:

- `cap_turnoverf_gt4` and `cap_pb_gt3p6` marginally reduce drawdown and extreme contribution;
- but they trail `roundtrip_m150` on return, OOS overlap, beta-hedged annualized return, and beta-hedged overlap;
- the reduction is too small to justify extra parameters.

The right next step is delayed-exit execution simulation, not more threshold tuning.
