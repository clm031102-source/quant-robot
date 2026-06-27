# CN Stock Round442 Incremental Range-Contraction Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round442 tests the first genuinely useful new direction after public technical overlays failed: capacity-safe price-volume `range_contraction_lowvol_reversal_20` as an incremental overlay on top of the current delayed-exit Alpha101/Dragon baseline.

Key distinction:

- Round441 single-factor rebuilds replaced the existing Alpha101 tilt and were weaker than base.
- Round442 uses the existing baseline `pre_overlay_return_contribution` and `pre_overlay_target_weight`, disables duplicate Dragon cash, adds the new factor as a second-layer tilt, then reruns entry-timed vol/self-risk.

## Construction

10 bps candidate:

- source trades: `data/reports/round432_24h_profit_sprint_delayed_exit_m150_20260627/cohort_trade_rows.csv`;
- return input: `pre_overlay_return_contribution`;
- weight input: `pre_overlay_target_weight`;
- public factor: `range_contraction_lowvol_reversal_20`;
- side: top 10%;
- multiplier: 1.50x;
- Dragon cash: disabled because it is already inside the base pre-overlay rows;
- vol target: 8%, lookback 84, max exposure 1.00;
- self-risk: prior 21 closed events below 0 gets 0.80x exposure.

Cost-stress variants:

- 20 bps: same overlay on Round433 cost20 base, VT 8%;
- 30 bps fallback: same overlay on Round433 cost30 base, VT 7.0% to keep full-sample drawdown inside the 30% risk line.

## Main Result

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | OOS Ann. | OOS Strict | Beta-Hedged Ann. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `base_cost10` | 6.663% | 218.46% | 0.968 | 0.496 | -26.21% | 41.33% | 10.043% | 90.00% | 7.502% |
| `incremental_range_cost10` | 7.083% | 241.70% | 0.984 | 0.505 | -26.99% | 41.99% | 10.695% | 90.00% | 8.004% |
| `base_cost20` | 6.060% | 187.60% | 0.888 | 0.456 | -28.07% | 41.22% | 9.132% | 76.67% | 6.744% |
| `incremental_range_cost20` | 6.458% | 207.62% | 0.905 | 0.466 | -28.87% | 41.44% | 9.744% | 90.00% | 7.241% |
| `base_cost30_vt075` | 5.415% | 157.79% | 0.809 | 0.416 | -29.66% | 40.55% | 8.197% | 76.67% | 5.952% |
| `incremental_range_cost30_vt070` | 5.581% | 165.17% | 0.821 | 0.422 | -29.97% | 41.10% | 8.307% | 76.67% | 6.183% |

## Robustness Notes

10 bps:

- leave-one-year minimum annualized return improved from 5.001% to 5.323%;
- leave-one-year minimum overlap Sharpe improved from 0.425 to 0.435;
- best-three-month concentration improved from 45.72% to 45.36%;
- beta-hedged overlap improved from 0.797 to 0.808;
- alpha t-stat improved from 4.40 to 4.48.

20 bps:

- annualized return improved from 6.060% to 6.458%;
- OOS strict pass improved from 76.67% to 90.00%;
- max drawdown worsened from -28.07% to -28.87%, still inside 30%.

30 bps:

- VT 7.5% version improved return but breached -30% full-sample drawdown;
- VT 7.0% version restored drawdown to -29.97%;
- OOS strict pass remains 76.67%, so it is a stress fallback, not a strong promotion lane.

## Statistical Reality Check

Round442 corrected the p-value policy to match earlier project usage: two-sided normal p-value from `overlap_newey_west_t_stat_mean`, not `overlap * sqrt(N)`.

Corrected result across six hypotheses:

- deflated-Sharpe pass count: 6;
- FDR significant count: 0;
- statistical candidate count: 0;
- best row: `incremental_range_cost10`;
- best p-value: 0.03229;
- common FDR q-value: 0.07777.

Interpretation: Round442 is the best new simulation-observation lead found in this sprint, but it is not statistically final alpha.

## Decision

Promote `incremental_range_cost10` to the active simulation-observation watchlist as the best return-seeking candidate found after the formal rebuild correction.

Carry:

- `incremental_range_cost20` as the heavy-cost observation lane;
- `incremental_range_cost30_vt070` as the stress fallback only.

Do not claim final profitability alpha until this survives the next three-round audit, a stricter bootstrap/CPCV check, and the project-level paper-simulation handoff review.
