# CN Stock Round447-449 Three Round Audit

Date: 2026-06-27

Scope: three-round process audit after Round447, Round448, and Round449. This
audit checks whether the sprint is still moving toward simulation-ready
profitable factors or drifting into parameter/data mining.

## Round Summary

Round447 tested a PB risk cap on the aggressive
`range_contraction_lowvol_reversal_20` q20/m175 lane. The useful result was
PB cap050 as a risk-budget variant. It improved overlap Sharpe and drawdown
under fair controls, but the statistical reality check still found 0
FDR-significant candidates across 15 hypotheses. Decision: simulation
observation only, not an alpha promotion.

Round448 tested entry-known valuation, turnover, capacity, board, and dividend
availability filters against the frozen low10 VT6/LB84 baseline. The best
projection-only leads were `ps_gt10` and `pb_gt6`, but their incremental return
was small and year-level consistency was not strong. Decision: keep as
valuation risk-filter observations only; stop widening PB/PS/PE thresholds.

Round449 audited trade group contribution, structural exposure, and entry/exit
tradeability losses. `entry_limit_down` is the cleanest economic observation:
avoid/cash names that are limit-down or limit-down-like at the intended entry.
Worst-industry cashing had better numbers but was selected from full-sample
contribution and is therefore data-snooping until rebuilt from an ex ante
hypothesis. Decision: no new alpha promotion; only `entry_limit_down` can move
to a formal execution-rule rebuild.

## Useful Results

- Best current handoff remains the Round446 delayed-exit default; range lanes
  are paper-simulation observations, not automatic replacements.
- `range_q10_m150` remains the best cost-robust range observation lane.
- `range_q20_m175` remains an aggressive 10 bps observation lane with heavier
  cost fragility.
- PB cap050 is a possible aggressive-lane risk-budget observation, not a return
  engine.
- `ps_gt10` and `pb_gt6` are minor projection-only valuation risk filters.
- `entry_limit_down` is the only new Round447-449 idea with a clean entry-known
  execution rationale.

## What Failed

- No Round447-449 candidate qualifies as a new independent alpha factor.
- Valuation-threshold widening is becoming parameter search with small
  incremental gains.
- Industry blacklist numbers are contaminated by full-sample selection.
- Exchange/board/HS filters improved some risk metrics only by removing return;
  they are not useful as simple filters.
- Exit-limit-down diagnostics use information unavailable at entry.

## Direction Change

Stop:

- range-contraction neighborhood widening;
- PB/PS/PE threshold tuning;
- full-sample industry blacklist tuning;
- structural filters that reduce return without a stronger objective.

Continue:

- formal cohort-entry rebuild of `entry_limit_down` if the code supports it or
  can be extended safely;
- compare the rebuild against the same Round339/Round446 baselines with cost,
  CPCV/bootstrap, leave-one-year, and concentration gates;
- if formal rebuild fails, rotate to a genuinely different point-in-time
  family rather than mutating the same projection filters.

## Gate For Next Work

Any next candidate must satisfy all of the following before simulation
shortlist discussion:

- known at the rebalance/entry decision time;
- generated before return realization, not selected from full-sample
  contribution;
- evaluated on the long 2015-2025 sample, with 2026 still sealed;
- run through transaction cost and capacity checks;
- audited for overlap-adjusted Sharpe, drawdown, win rate, block robustness,
  CPCV/bootstrap, and concentration;
- explicitly tagged as final alpha, simulation observation, diagnostic, or
  rejected.

Safety: research-to-review only. No broker access, no account reads, no orders,
and no live trading.
