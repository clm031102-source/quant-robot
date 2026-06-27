# CN Stock Rounds 421-423 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

Rounds 421-423 corrected a serious handoff risk.

The project should no longer call aggregate exit-date event streams "paper-ready" unless they preserve entry/exit cohort timing. The current true paper-ready candidate is the cohort-level Alpha101 open-close lane.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 421 | Signal reconstruction and cohort repair | Aggregate Round419 stream fails paper-readiness; cohort-level builder added | Use cohort candidate as true handoff |
| 422 | Formal replay/ranking | 17 candidates replay; aggregate stream blocked as not paper-ready; cohort candidate ranks #3 overall | Ranking now distinguishes research observations from paper candidates |
| 423 | Cost stress | 5/10 bps pass user drawdown tolerance; 20/30 bps remain profitable but breach -30% max drawdown | 10 bps cohort candidate is current handoff; heavier-cost simulation needs lower-risk grid |

## Best True Paper Candidate

`paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

| Metric | Value |
|---|---:|
| total return | +163.48% |
| annualized return | 5.76% |
| Sharpe | 0.863 |
| overlap Sharpe | 0.466 |
| max drawdown | -29.18% |
| mean OOS annualized return | 8.53% |
| OOS strict pass rate | 90.00% |
| beta-hedged annualized return | 6.23% |
| beta-hedged max drawdown | -15.10% |

## Process Rule Added

Promotion to paper simulation requires cohort-level signal reconstruction when the underlying event source can contain overlapping entry cohorts.

Aggregate event returns may stay in the research leaderboard, but they cannot be handed to simulation unless entry-decision alignment is proven.

## Next Direction

Round424 should run a heavier-cost cohort risk-budget grid for 20/30 bps assumptions, or build the paper-simulation adapter around the 10 bps cohort candidate if 10 bps is the intended starting cost assumption.
