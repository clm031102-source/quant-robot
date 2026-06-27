# CN Stock Round412 - Self-Risk Event Schema Repair

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Problem

Round411 replay exposed a simulation-readiness defect in self-risk overlay outputs.

The self-risk overlay preserved return math, but dropped source event structure. That made strong candidates such as `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` numerically attractive but structurally incomplete for simulation replay.

## Root Cause

`build_shortlist_self_risk_overlay` loaded sources through `load_candidate_period_returns()`. That helper intentionally reduces event sources to:

- `date`
- `period_return`

That is correct for return metric audits, but wrong for an overlay that writes a new event stream for later simulation. The source columns were lost before `_apply_policy()` ran.

## Fix

`src/quant_robot/ops/shortlist_self_risk_overlay.py` now:

- loads an enriched event frame when the source has event schema columns;
- preserves source metadata such as `decision_date`, `riskoff_multiplier`, and `regime_guard_exposure`;
- records `source_final_exposure` before applying self-risk;
- writes final exposure as `source_final_exposure * self_risk_exposure`.

Added test coverage:

- `test_overlay_preserves_event_schema_and_combines_final_exposure`

## Regenerated Evidence

Regenerated the five self-risk event streams currently referenced by the simulation shortlist:

- Qlib top10 self-risk
- Alpha101 open-close self-risk
- Dragon-Hot self-risk
- ADX full-source self-risk
- PS Dragon self-risk

The output paths stayed unchanged, so the config does not need path changes.

## Verification

Round412 replay:

- output: `data/reports/round412_24h_profit_sprint_simulation_shortlist_replay_after_schema_repair_20260627`
- status: passed
- candidate count: 14
- replayed candidates: 14
- blocked candidates: 0
- blockers: 0

Round412 ranking:

- output: `data/reports/round412_24h_profit_sprint_simulation_shortlist_ranking_after_schema_repair_20260627`
- best candidate: `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`
- unique simulation observations: 5
- duplicate streams: 9

## Decision

The strongest current candidate is now both numerically replayable and structurally replayable.

This repair should be considered a prerequisite before simulated paper replay. It does not promote any candidate by itself; it makes the evidence chain cleaner.
