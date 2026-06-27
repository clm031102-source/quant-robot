# CN Stock Rounds 411-413 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

Rounds 411-413 improved the simulation-readiness process more than the raw factor count.

The best current candidate remains:

`primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

It is now both numerically replayable and structurally replayable, and no tested blend beats it.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 411 | Simulation shortlist ranking and duplicate audit | 14 configured candidates collapse to 5 unique observations; 9 are near-duplicate streams | Use ranker for future shortlist triage |
| 412 | Self-risk event schema repair | Replay blockers drop from 15 schema issues to 0 | Make schema-preserving self-risk overlay mandatory before simulation |
| 413 | Unique-candidate blend search | 70 blends tested; 100% top Alpha101 self-risk remains best | Do not add blended candidate |

## Best Candidate

`primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

- total return: +232.15%
- annualized return: 7.52%
- Sharpe: 1.229
- overlap Sharpe: 0.645
- max drawdown: -16.45%
- OOS mean annualized return: 8.05%
- OOS worst drawdown: -13.44%
- beta-hedged annualized return: 7.49%
- beta-hedged overlap Sharpe: 1.023
- beta-hedged max drawdown: -9.71%

## Process Upgrades

- Added a reusable simulation shortlist ranker with tests and CLI.
- Repaired self-risk overlay event schema preservation.
- Verified all 14 shortlist candidates replay cleanly after repair.
- Confirmed candidate blending does not improve the current best lane.

## What This Means

The project should not spend the next cycle tuning Alpha101/Qlib/Dragon-Hot relatives or blending the same streams.

The next high-value direction is independent-source discovery with enough point-in-time coverage, or a direct paper-simulation harness around the current best candidate.

## Next Direction

Round414 should rotate away from the current correlated cluster. Preferred lanes:

- independent event/accounting source with sufficient PIT coverage;
- execution/capacity-aware simulation harness for the current best candidate;
- ETF-translation research only if explicitly switching task scope back to ETF rotation.
