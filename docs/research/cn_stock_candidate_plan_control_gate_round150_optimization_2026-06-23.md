# CN Stock Candidate Plan Control Gate Round150 Optimization

## Purpose

This round optimizes the mining process before continuing factor discovery. The immediate problem was not one specific bad factor. The problem was that a new family could still start from a plausible public idea without explicitly declaring all controls needed for A-share tradability, PIT timing, neutralization, portfolio construction, strict statistics, China regime, and event contamination.

## Implemented Changes

- Added `factor_mining_candidate_plan_gate`, a reusable pre-mining gate for CN stock factor candidate plans.
- Added `scripts/run_factor_mining_candidate_plan_gate.py` to turn any preregistration JSON into a gate packet.
- Added a default CN stock pre-mining control plan covering eight areas:
  - A-share tradeability.
  - Financial/PIT timing.
  - Industry and style neutralization.
  - ETF rotation scope boundary.
  - Portfolio construction beyond raw TopN.
  - Strict statistics.
  - China market regime.
  - Event factor or event-contamination controls.
- Added the control plan to the active lottery/MAX-effect preregistration artifact.
- Added startup-gate protocol items so future runs must confirm the candidate plan gate before factor generation.

## Live Gate Result

Command output location:

- `data/reports/factor_mining_candidate_plan_gate_round150_optimization_20260623`

Result:

- Status: `research_ready`.
- Candidates checked: 6.
- Complete control areas: 8 / 8.
- Research screen allowed: true.
- Portfolio grid allowed: false.
- Promotion allowed: false.
- Quality gate status: `classified`, not promotion-ready.

## Interpretation

This is the right gate state. The active Round150 lottery/MAX-effect family may proceed to IC and neutral prescreen, but cannot jump to portfolio construction or promotion. The broader quality gate still shows planned/partial controls, especially portfolio construction and China-specific regime data. Those must remain promotion blockers until implemented evidence exists.

## Next Action

Proceed to Round150 lottery extreme-upside reversal IC/neutral prescreen under the new gate. If the prescreen fails, rotate the family instead of tuning formulas. If it passes, the next gate is reference/redundancy dedup plus limit-path tradeability audit before any portfolio conversion.
