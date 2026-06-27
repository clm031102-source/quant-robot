# CN Stock 24h Profit Sprint - Round456-458 Audit

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: required three-round review after Round456, Round457, and Round458.

## Executive Decision

Round456-458 produced 0 new independent alpha factors and 0 final promoted signals.

The work was still useful because it converted the current strongest high-return observation into a controlled paper-simulation package:

- default comparison lane: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- high-return paper lane: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`

The high-return lane is ready for paper observation, not final promotion.

## Round456

Direction: apply the user's drawdown tolerance to current paper handoff ranking.

Result:

- paper handoff candidates: 8
- ready candidates: 5
- blocked candidates: 3
- default lane: annualized 6.663%, total +218.46%, max drawdown -26.21%, OOS strict pass 90%
- primary high-return lane: annualized 7.723%, total +280.30%, max drawdown -29.31%, OOS strict pass 90%

Decision: keep the default lane for baseline comparison and mark `range_q20_m175` as the primary high-return paper lane under the user's 30% soft drawdown tolerance.

## Round457

Direction: harden `range_q20_m175` before paper simulation.

Result:

- current shortlist replay passed for 17 candidates
- event schema contains decision date, final exposure, period return, equity, and drawdown fields
- capacity safe through 20x AUM under 5% ADV participation
- capacity unsafe from 50x AUM
- 10 bps profile stays within -30% drawdown
- 20 to 30 bps stress crosses the -30% soft drawdown line
- 123 extreme trades contribute about 35.2% of total contribution

Decision: retain `range_q20_m175` as a 10 bps high-return paper lane, with cost and tail-risk warnings. Do not promote it or widen its parameters.

## Round458

Direction: package default and high-return lanes into a repeatable paper-operations artifact.

Result:

- package status: `paper_ops_package_ready`
- blockers: 0
- ready paper lanes: 2
- generated artifact: `data/reports/round458_24h_profit_sprint_simulation_paper_ops_package_20260627`
- reusable tool: `scripts/run_simulation_paper_ops_package.py`

The package explicitly carries these warnings:

- final holdout remains sealed
- high-return lane is still a diagnostic role
- high-return drawdown is near the user limit
- high-return beta-hedged metrics are missing in the current handoff
- heavier cost stress breaches the soft drawdown limit
- tail contribution is concentrated
- large-AUM capacity is not clean
- shortlist streams are highly correlated

## Audit Conclusion

This three-round block did not discover a new alpha family. It improved deployment readiness for the best current observation.

That means the next mining block must not continue:

- range parameter widening
- same-family range/Alpha101/Dragon-Hot projections
- weight blending among highly correlated shortlist streams
- promotion claims from paper-ready status alone

## Next Direction

Round460 should rotate to an independent long-cycle prescreen.

Allowed next candidates:

- overnight/intraday gap behavior
- information discreteness
- 52-week-high quality
- public trend-strength state only if it is not a SuperTrend/RSRS retread

The next run must use long-cycle data, keep 2026 final holdout sealed, and record candidates before accepting any result as a lead.
