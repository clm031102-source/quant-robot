# CN Stock Rounds 460-462 Three-Round Audit

Date: 2026-06-27

Scope: closeout audit for the final three rounds of the 24h CN stock profitability sprint. This audit stops new mining and records what can be carried into paper simulation versus what must stay rejected or hibernated. The 2026 final holdout remains sealed.

## Round Results

| Round | Direction | Result | Decision |
| --- | --- | --- | --- |
| 460 | Independent long-cycle prescreen: 52-week quality, overnight/intraday gap, information discreteness | 52-week quality produced statistically significant wrong-way IC; gap and FIP re-entry were blocked by historical zero-lead evidence or memory-safe path constraints | 0 new alpha, 0 paper-ready signal, hibernate re-entry without new orthogonal hypothesis |
| 461 | High-return q20/m175 benchmark beta audit | q20/m175 was not only hidden CSI500 beta: CSI500 beta `0.0492`, R2 `0.2391`, alpha t-stat `5.3167`, hedged annualized `0.0862` | Beta gap closed, but no final promotion because cost/tail/capacity risks remained |
| 462 | q20/m175 high-return risk repair with entry-known `ps_ttm > 10` cash-out | Added one paper-simulation risk-repair lane; cost10 DD improved to `-0.2542`, cost30 DD `-0.2813`, ops package ready with 0 blockers | 1 new paper-ready observation lane, 0 independent new alpha, 0 final promotion |

## Best Current Paper Lanes

Baseline lane:

- Candidate: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- Role: conservative/default paper comparison lane
- Reason kept: it is the most stable default lane and must remain side by side with any higher-return diagnostic lane.

High-return paper observation lane:

- Candidate: `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08`
- Role: diagnostic high-return observation, not final alpha
- Cost10 total return: `2.8484884757`
- Cost10 annualized return: `0.0779414358`
- Cost10 overlap Sharpe: `0.5654308054`
- Cost10 max drawdown: `-0.2542482237`
- OOS strict pass rate: `0.7666666667`
- CSI500 beta-hedged annualized return: `0.0858911865`
- CSI500 beta-hedged max drawdown: `-0.1129940427`
- Cost30 total return: `1.9697047343`
- Cost30 annualized return: `0.0624920505`
- Cost30 max drawdown: `-0.2813099618`
- Cost30 OOS strict pass rate: `0.6333333333`

## Paper Ops Status

- Handoff output: `data/reports/round462_24h_profit_sprint_ps_gt10_paper_handoff_20260627`
- Paper ops output: `data/reports/round462_24h_profit_sprint_ps_gt10_paper_ops_package_20260627`
- Paper ops status: `paper_ops_package_ready`
- Blockers: `0`
- Ready paper lanes: `2`
- Final holdout: `sealed`
- Live boundary allowed: `false`
- Worst candidate-level cost-stress drawdown: `-0.2813099618`

Remaining warnings:

- `capacity_not_clean_at_large_aum`
- `default_lane_kept_for_baseline_not_return_maximization`
- `final_holdout_sealed_promotion_blocked`
- `high_return_lane_is_diagnostic_role`
- `high_return_tail_contribution_concentrated`
- `shortlist_streams_highly_correlated`

## What Improved

The q20/m175 high-return lane became usable for paper observation after Round462:

- Max drawdown improved from about `-0.2931` to `-0.2542`.
- Cost30 max drawdown improved into the user tolerance band at `-0.2813`.
- CSI500 beta-hedged overlap Sharpe stayed strong at `0.9299` for cost10 and `0.7755` for cost30.
- Extreme contribution share fell only slightly, from about `35.21%` to `34.52%`, so tail risk is improved but not solved.
- Capacity is safe through `20x` and unsafe from `50x`, so sizing must stay conservative.

## What Failed

Round460 confirmed that forcing new candidates from old weak sources is low value:

- Direct 52-week high-quality behaved wrong-way over the long cycle.
- Inverse 52-week overextension had already failed earlier full validation and must not be re-opened by parameter tuning.
- Overnight/intraday gap and information discreteness remain hibernated unless a new orthogonal implementation or data source changes the hypothesis.

The broader sprint also showed that more parameter search is not the bottleneck. The bottleneck is finding genuinely independent, point-in-time information that survives long-cycle replay, costs, capacity, beta, tail, and regime checks.

## Decisions

1. Stop new mining for this closeout.
2. Carry two lanes into the reportable paper-simulation package: the default delayed-exit lane and the ps_gt10 high-return risk-repair lane.
3. Do not promote any lane to final/live use. The final holdout is still sealed, and this project remains research-to-paper only.
4. Hibernate Round460 rejected families and q20 same-family parameter extensions until a new orthogonal data source or hypothesis is documented.
5. If work resumes after this closeout, the next allowed work is either paper-simulation packaging/monitoring preparation or a genuinely new PIT source. It should not be more q20 threshold tuning.

## Counts

- New independent alpha factors from Rounds 460-462: `0`
- New paper-ready observation lanes from Rounds 460-462: `1`
- New final promotion candidates from Rounds 460-462: `0`
- Paper ops blockers after Round462: `0`
- Remaining paper ops warnings: `6`
