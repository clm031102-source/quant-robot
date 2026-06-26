# CN Stock Quality Gate Research Execution Policy Round194

Date: 2026-06-23

## Purpose

Round194 converts the user's eight optimization concerns into a hard pre-mining execution policy. The goal is to stop direct parameter mining when the project has unresolved tradeability, point-in-time, neutralization, portfolio, regime, or event-data controls.

This is a process-optimization round, not a factor-discovery round. It produced zero new profitability factors.

## What Changed

- Added a `research_execution_policy` section to the CN stock factor-mining quality gate.
- Surfaced that policy in the startup gate checklist before every new factor-mining run.
- Added protocol items requiring:
  - quality-gate execution policy review before mining,
  - direct factor generation to stay blocked until pre-mining controls are ready,
  - candidate preregistration without profit claims when controls are incomplete.
- Added a scope-aware exception so the unfinished CN ETF dedicated signal pack blocks ETF/promotion work but does not incorrectly block CN stock factor research.

## Current Gate Result

Latest generated packets:

- `data/reports/round194_quality_gate_execution_policy_optimization_20260623/factor_mining_quality_gate.json`
- `data/reports/round194_startup_gate_execution_policy_optimization_20260623/factor_mining_startup_gate.json`

Quality gate status:

- Total controls: 34
- Implemented controls: 10
- Partial controls: 17
- Planned controls: 7
- Missing controls: 0
- Missing evidence controls: 0
- Missing next-action controls: 0
- Promotion cleared: false

Execution policy:

- Direct factor generation allowed: false
- Candidate preregistration allowed: true
- Data coverage audit allowed: true
- Portfolio grid allowed: false
- Promotion claim allowed: false

Allowed next work modes:

- quality control implementation
- data coverage audit
- candidate preregistration without profit claims

Blocked next work modes:

- direct parameter grid mining
- fresh factor screen without control closeout
- portfolio grid
- promotion claim

## Remaining Direct-Mining Blockers

Direct CN stock factor generation remains blocked by these unresolved control groups:

- Real tradeability: official limit-up/down, suspension, and PIT delisting controls are still partial.
- Financial PIT timing: announcement-date alignment is partial, revision handling is planned, and report-period-only safeguards need a harder gate.
- Industry/style neutralization: exposure reports, style decomposition, and residual options exist only for selected families, not as universal pre-mining controls.
- Portfolio construction: risk budget sizing, volatility targeting, industry weights, turnover hard limits, and de-risk rules are not fully implemented.
- China regime: SHIBOR/index/margin/northbound regime data exists in pieces, but regime coverage is not a universal pre-mining requirement.
- Event factors: forecast, dividend, buyback/holder/unlock, and index-rebalance paths are not ready for promotion; index-rebalance data is still planned.

## Direction Change

The startup config now points to:

`round195_quality_control_closeout_or_data_readiness_audit_before_direct_factor_generation`

This means the next round should not continue blind public-indicator or parameter mining. It should prioritize which missing controls are cheapest and most valuable to close, then either:

- implement the top control gap,
- run a data-readiness audit for the top data-dependent gap, or
- preregister a candidate family only if it does not make profitability claims before controls are ready.

## Verification

The relevant unit suite passed after the policy change:

`python -m unittest tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_candidate_plan_gate tests.unit.test_factor_mining_candidate_plan_gate_cli`

Result: 46 tests OK.

