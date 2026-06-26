# CN Stock Round227 Public-Method Family Rotation - 2026-06-24

## Purpose

Round226 added the method optimization contract and blocked two expensive reentry mistakes:

- continuing the financial post-announcement gap-reversal family after Round225 found zero accepted walk-forward cases;
- reopening public risk-filter bridge, SuperTrend, or single trend-volume paths after their translation layers failed.

Round227 applies that contract to choose the next mining family.

## Inputs

- Startup gate: `data/reports/factor_mining_startup_gate_round226_method_optimization_contract_20260624/factor_mining_startup_gate.json`
- Candidate families: `configs/family_rotation_candidates_round227_public_method_family_rotation_20260624.json`
- Candidate plan seed: `configs/family_rotation_seed_round227_public_method_family_rotation_20260624.json`
- Candidate plan gate output: `data/reports/round227_public_method_family_rotation_candidate_plan_gate_20260624`
- Rotation output: `data/reports/cn_stock_family_rotation_decision_round227_public_method_family_rotation_20260624`

## Family Rotation Result

Selected family:

`public_anomaly_residual_ensemble_risk_budget`

Decision:

- Rotation status: cleared
- Families reviewed: 10
- Hibernated families: 8
- Data-gap families: 1
- Blockers: 0
- Next direction: `round228_public_anomaly_residual_ensemble_preregistration`
- Portfolio grid allowed: false
- Promotion allowed: false

Hibernated families included:

- `financial_post_announcement_gap_reversal`
- `public_risk_filter_bridge`
- `public_supertrend_or_single_trend_volume`
- `public_trend_strength_state_residual`
- `industry_leader_lag`
- `information_discreteness`
- `direct_profitability_quality_formula_tuning`
- `external_northbound_crowding_reversal`

Data-gap family:

- `buyback_holder_unlock_event_alpha`

## Candidate Plan Gate Result

Candidate plan:

`configs/family_rotation_seed_round227_public_method_family_rotation_20260624.json`

Result:

- Status: `research_ready`
- Candidate count: 4
- Blockers: 0
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

Pre-registered candidate seeds:

| Candidate | Purpose |
|---|---|
| `public_anomaly_residual_equal_weight_20` | Fixed-weight blend of public anomaly components after residualization. |
| `public_anomaly_residual_agreement_20` | Requires agreement across independent public anomaly components. |
| `public_anomaly_residual_disagreement_risk_20` | Uses disagreement as an exclusion/risk diagnostic, not a buy signal. |
| `public_anomaly_residual_regime_conditioned_20` | Adds lagged China regime conditioning with explicit signal-window coverage. |

## Why This Direction

The project has repeatedly failed when it treated one indicator family as a direct TopN alpha. Round227 therefore selects a method family that changes the structure:

- fixed public anomaly components instead of learned weights;
- industry/style residualization before portfolio conversion;
- tradeability masks and survivorship controls before factor generation;
- multiple-testing and parameter-sensitivity accounting from the start;
- China regime signal-window coverage before promotion review;
- no use of hibernated public risk-filter or gap-reversal lines as standalone alpha.

This is still a hypothesis, not a profitability result.

## Decision

Promotable profitable factors from Round227: 0.

Paper-ready factors from Round227: 0.

Useful result: one controlled next family and four pre-registered candidate seeds, with portfolio grids and promotion explicitly blocked.

## Next Direction

Round228 should implement or reuse a factor-source/preregistration path for:

`round228_public_anomaly_residual_ensemble_preregistration`

The next round must produce only preregistration and/or residual IC gate evidence first. It must not run a portfolio grid until the candidate plan, residual IC/shape, source-correlation dedup, tradeability, regime, and multiple-testing gates clear.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
