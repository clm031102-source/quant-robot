# CN Stock Round461 High-Return Beta Audit

Date: 2026-06-27

Scope: paper-readiness hardening for the current high-return CN stock paper-simulation lane. This is diagnostic evidence only; the 2026 final holdout remains sealed.

## Candidate

- Candidate: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`
- Mechanism: delayed-exit m150 base plus `range_contraction_lowvol_reversal_20` top-20% incremental entry tilt at 1.75x, entry-timed volatility target 8%, max exposure 1.00, and self-risk `roll21_sum_neg_0.80x`.
- Event source: `data/reports/round445_24h_profit_sprint_range_contraction_incremental_sensitivity_20260627/round445_range_q20_m175/simulation_shortlist_entry_timed_events.csv`

## Method

1. Reconstructed event-frequency benchmark returns from local ETF adjusted close data.
2. Used each strategy event's `decision_date` as the benchmark entry date and event `date` as the exit date.
3. Audited exposure against HS300 proxy `CN_ETF_XSHG_510300` and CSI500 proxy `CN_ETF_XSHG_510500`.
4. Kept the result as a diagnostic exposure audit, not as a promotion gate or final holdout read.

Output directory:

`data/reports/round461_24h_profit_sprint_high_return_beta_audit_20260627`

## Key Results

Against CSI500:

- Beta: `0.0491893930`
- R-squared: `0.2391101281`
- Alpha annualized: `0.0850255800`
- Alpha t-stat: `5.3166858810`
- Strategy annualized return: `0.0772282690`
- Strategy total return: `2.8030242437`
- Strategy max drawdown: `-0.2931481649`
- Beta-hedged annualized return: `0.0861909878`
- Beta-hedged overlap Sharpe: `0.9082790905`
- Beta-hedged max drawdown: `-0.1129057538`

Against HS300:

- Beta: `0.0591963320`
- R-squared: `0.1958925073`
- Alpha annualized: `0.0848150894`
- Alpha t-stat: `5.1590337702`
- Beta-hedged annualized return: `0.0858255798`
- Beta-hedged overlap Sharpe: `0.7575476950`
- Beta-hedged max drawdown: `-0.3244613390`

Comparison against CSI500:

| candidate | beta | r2 | hedged ann | hedged overlap Sharpe | hedged max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| default_delayed_exit_m150 | 0.043970 | 0.240847 | 0.074494 | 0.883190 | -0.107857 |
| range_q10_m150 | 0.045705 | 0.238648 | 0.079053 | 0.890825 | -0.106177 |
| range_q20_m175 | 0.049189 | 0.239110 | 0.086191 | 0.908279 | -0.112906 |

## Decision

Round461 closes the missing beta-hedged evidence gap for the high-return lane. The q20/m175 candidate is not merely hidden CSI500 beta: it improves beta-hedged annualized return and overlap Sharpe versus the default and q10 lanes without a material increase in R-squared.

Refreshed paper handoff:

- Output: `data/reports/round461_24h_profit_sprint_beta_refreshed_paper_handoff_20260627`
- Ready candidates: `5 / 8`
- Primary high-return candidate: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`
- Primary high-return total return: `2.8030242437`
- Primary high-return annualized return: `0.0772282690`
- Primary high-return max drawdown: `-0.2931481649`

Refreshed paper ops package:

- Output: `data/reports/round461_24h_profit_sprint_beta_refreshed_paper_ops_package_20260627`
- Status: `paper_ops_package_ready`
- Blockers: `0`
- Ready lanes: `2`
- The prior `high_return_beta_hedged_metrics_missing` warning is closed.
- Remaining warnings: `capacity_not_clean_at_large_aum`, `default_lane_kept_for_baseline_not_return_maximization`, `final_holdout_sealed_promotion_blocked`, `high_return_cost_stress_drawdown_below_user_limit`, `high_return_drawdown_near_user_limit`, `high_return_lane_is_diagnostic_role`, `high_return_tail_contribution_concentrated`, `shortlist_streams_highly_correlated`.

It is still not a final promotable alpha. The remaining hard risks are:

- Raw full-sample max drawdown is near the user's soft tolerance at `-29.31%`.
- Heavier cost stress has already pushed drawdown beyond 30% in Round457.
- Extreme-trade contribution remains concentrated at about 35%.
- Capacity is safe through 20x but unsafe from 50x in the current stress package.
- Final 2026 holdout remains sealed and must not be used for tuning.

Next direction: Round462 should either repair tail/cost/capacity risk for the high-return lane or rotate to a genuinely new point-in-time source. Do not reopen Round460 52-week/FIP/OHLC-gap families without a new orthogonal mechanism.
