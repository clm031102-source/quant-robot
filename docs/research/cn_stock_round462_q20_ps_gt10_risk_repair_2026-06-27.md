# CN Stock Round462 Q20 PS>10 Risk Repair

Date: 2026-06-27

Scope: paper-readiness risk repair for the high-return q20/m175 CN stock lane. This is a point-in-time trade-attribute overlay on an existing paper-simulation candidate, not a new promotable alpha. The 2026 final holdout remains sealed.

## Candidate

- Base lane: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`
- Repair rule: cash out active trade contribution when entry-known `ps_ttm > 10`
- Output return stream: `data/reports/round462_24h_profit_sprint_q20_tail_attribute_cash_filter_20260627/cash_ps_gt_10_official_template_period_returns.csv`
- Filtered trade rows: `data/reports/round462_24h_profit_sprint_q20_ps_gt10_filtered_trades_20260627/cohort_trade_rows_ps_gt10_cash.csv`

## First-Pass Attribute Screen

Six single-rule, entry-known filters were tested: `pb > 8`, `ps_ttm > 10`, `turnover_rate_f > 8`, `circ_mv < 300000`, `participation_rate > 0.00025`, and `final_target_weight > 0.007`.

The only rule that improved both drawdown and risk-adjusted quality without sacrificing return was `ps_ttm > 10`:

- Flagged trades: `2351`
- Flagged share: `8.89%`
- Flagged original contribution sum: `0.0066425519`
- Flagged original absolute contribution sum: `0.5565755232`

## Cost10 Metrics

- Total return: `2.8484884757`
- Annualized return: `0.0779414358`
- Sharpe: `1.0852924335`
- Overlap Sharpe: `0.5654308054`
- Max drawdown: `-0.2542482237`
- Win rate: `0.4187845304`
- Leave-one-year min annualized return: `0.0589699798`
- Leave-one-year min overlap Sharpe: `0.4730037914`

## OOS And Incremental Robustness

OOS:

- Mean OOS annualized return: `0.1164424899`
- Mean OOS overlap Sharpe: `0.9448615203`
- Positive OOS rate: `0.9000000000`
- Strict OOS pass rate: `0.7666666667`
- Worst OOS drawdown: `-0.2088114911`

Incremental versus unfiltered q20/m175:

- Delta annualized return: `0.0007131667`
- Delta total return: `0.0454642320`
- Delta overlap Sharpe: `0.0533845687`
- Delta max drawdown: `0.0388999413`
- CPCV annualized win rate: `0.5583333333`
- CPCV drawdown win rate: `0.9666666667`
- CPCV overlap win rate: `0.9416666667`
- CPCV strict pass rate: `0.5000000000`
- Bootstrap annualized win rate: `0.5400000000`
- Bootstrap drawdown win rate: `0.9820000000`
- Bootstrap overlap win rate: `0.9780000000`
- Bootstrap strict pass rate: `0.3160000000`

Interpretation: the rule is a robust drawdown/overlap repair, not a robust return enhancer.

## Beta Audit

Against CSI500 at 10bps:

- Beta: `0.0440139202`
- R-squared: `0.2254740140`
- Alpha annualized: `0.0844399433`
- Alpha t-stat: `5.6795367058`
- Beta-hedged annualized return: `0.0858911865`
- Beta-hedged overlap Sharpe: `0.9299242994`
- Beta-hedged max drawdown: `-0.1129940427`

Against CSI500 at 30bps:

- Beta: `0.0437888729`
- R-squared: `0.2244905474`
- Alpha annualized: `0.0699364108`
- Alpha t-stat: `4.7148712017`
- Beta-hedged annualized return: `0.0702874310`
- Beta-hedged overlap Sharpe: `0.7755150228`
- Beta-hedged max drawdown: `-0.1272074840`

## Cost Stress

Approximate trade-level additional cost was applied as `(new_cost - 10bps) * final_target_weight` by delayed exit date.

| cost | total | annualized | overlap Sharpe | max DD |
| --- | ---: | ---: | ---: | ---: |
| 10bps | `2.8484884757` | `0.0779414358` | `0.5654308054` | `-0.2542482237` |
| 20bps | `2.3807147242` | `0.0701897972` | `0.5144051691` | `-0.2677939569` |
| 30bps | `1.9697047343` | `0.0624920505` | `0.4629553008` | `-0.2813099618` |

Cost30 OOS:

- Mean OOS annualized return: `0.0944778776`
- Mean OOS overlap Sharpe: `0.7717213035`
- Positive OOS rate: `0.7666666667`
- Strict OOS pass rate: `0.6333333333`
- Worst OOS drawdown: `-0.2224267642`

## Capacity And Tail

Capacity:

- Safe through AUM multiplier: `20x`
- Unsafe from AUM multiplier: `50x`
- 50x breach trades: `5`
- 100x breach trades: `465`

Tail concentration:

- Active trades after filter: `23806`
- Extreme trades: `116`
- Extreme contribution share: `0.3451793270`
- Original q20 extreme contribution share: `0.3520976237`

## Paper Ops Package

After rebuilding the paper handoff and simulation paper-ops package with candidate-level cost-stress evidence:

- Paper handoff output: `data/reports/round462_24h_profit_sprint_ps_gt10_paper_handoff_20260627`
- Paper ops output: `data/reports/round462_24h_profit_sprint_ps_gt10_paper_ops_package_20260627`
- Paper ops status: `paper_ops_package_ready`
- Blockers: `0`
- Ready lanes: `2`
- Default lane: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- Primary high-return lane: `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08`
- Candidate-level worst cost-stress drawdown used by ops package: `-0.2813099618`

Remaining warnings:

- `capacity_not_clean_at_large_aum`
- `default_lane_kept_for_baseline_not_return_maximization`
- `final_holdout_sealed_promotion_blocked`
- `high_return_lane_is_diagnostic_role`
- `high_return_tail_contribution_concentrated`
- `shortlist_streams_highly_correlated`

The stale Round457 cost-stress warning was removed after the ops package was fixed to prefer the current high-return candidate's own cost-stress evidence. This avoids applying the unfiltered q20 lane's cost30 drawdown to the ps_gt10 risk-repair lane.

## Decision

Promote `ps_ttm > 10` cash as a paper-simulation observation lane and a high-return risk-repair variant. It improves the best current q20 lane on cost10 return, max drawdown, overlap Sharpe, CSI500 beta exposure, and approximate 20/30bps drawdown.

Do not promote it as final alpha:

- OOS strict pass drops from the unfiltered q20/m175 `0.9000` to `0.7667`.
- Cost30 strict OOS pass is only `0.6333`.
- Capacity is still unsafe from 50x.
- Tail contribution share only improves from about `35.21%` to `34.52%`.
- The overlay was selected after observing prior q20 risk failures, so it remains a paper-simulation risk-repair candidate rather than a fresh independent discovery.

Next direction: run the three-round audit for Rounds 460-462, then either continue with this cost-robust paper lane packaging or rotate to a genuinely new PIT source if the audit says the q20 family is consuming too much budget.
