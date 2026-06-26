# CN Stock Quality Gate Evidence/Action Optimization - Round178

Date: 2026-06-23

## Purpose

This optimization turns the eight user-requested quality issues into an auditable pre-mining gate:

- A-share tradeability constraints.
- Point-in-time financial announcement timing.
- Industry/style neutralization.
- CN stock vs CN ETF scope boundary.
- Portfolio construction beyond raw TopN.
- Strict statistics and multiple-testing controls.
- China market regime context.
- Event-factor coverage and contamination checks.

## Code Changes

- `factor_mining_quality_gate` now requires:
  - evidence for every `implemented`, `partial`, and `not_applicable` control.
  - a next action for every `partial` and `planned` control.
  - explicit blocker counts for missing evidence and missing next actions.
- Quality-gate markdown now prints `Evidence` and `Next action` per control.
- `factor_mining_startup` now surfaces `missing_evidence` and `missing_next_actions` in the pre-run checklist.
- The repeatable mining protocol now requires:
  - `quality_gate_evidence_next_action_ledger`
  - `quality_gate_evidence_next_actions_confirmed`
- Default CN stock configs now include next actions for all partial/planned controls.

## Current Gate Result

Generated artifacts:

- `data/reports/round178_quality_gate_evidence_next_actions_20260623/factor_mining_quality_gate.json`
- `data/reports/round178_quality_gate_evidence_next_actions_20260623/factor_mining_quality_gate.md`
- `data/reports/round178_startup_gate_after_quality_optimization_20260623/factor_mining_startup_gate.json`
- `data/reports/round178_startup_gate_after_quality_optimization_20260623/factor_mining_startup_gate.md`

Quality gate summary:

- Status: `classified`
- Total controls: 34
- Implemented: 10
- Partial: 17
- Planned: 7
- Missing controls: 0
- Missing evidence controls: 0
- Missing next-action controls: 0
- Startup gate cleared: true
- Promotion gate cleared: false

## Interpretation

This does not create a profitable factor. It makes the mining process harder to fool.

The project can continue controlled CN stock data/factor preparation because no control is missing and every incomplete control has a next action. However, no candidate can be promoted as paper-ready while 17 controls are partial and 7 are planned.

The next permitted direction remains:

`round178_external_feed_sixth_monthly_shard_202507_continue_controlled_backfill`

That direction is data/matrix readiness work, not a profitability claim.

## Verification

- Red tests were first added for missing evidence and missing next actions.
- After implementation, quality-gate and startup-gate tests passed:
  - `tests.unit.test_factor_mining_quality_gate`
  - `tests.unit.test_factor_mining_quality_gate_cli`
  - `tests.unit.test_factor_mining_startup_gate`
  - `tests.unit.test_factor_mining_startup_gate_cli`
