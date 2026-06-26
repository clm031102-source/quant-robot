# CN Stock Round228 Public Anomaly Residual Ensemble Preregistration - 2026-06-24

## Purpose

Round227 selected `public_anomaly_residual_ensemble_risk_budget` as the next family. Round228 turns that decision into reusable project code.

This is still not a profitability claim:

- portfolio grid allowed: false;
- promotion allowed: false;
- final holdout: not touched;
- next required step: long-cycle residual IC/shape prescreen.

## Implemented Factor Source

New module:

`src/quant_robot/factors/daily_basic_public_anomaly_residual_ensemble.py`

Registered factor names:

- `public_anomaly_residual_equal_weight_20`
- `public_anomaly_residual_agreement_20`
- `public_anomaly_residual_disagreement_risk_20`
- `public_anomaly_residual_regime_conditioned_20`

The factor source uses fixed public-anomaly components:

- value proxy from `pe_ttm`, `pb`, and `dv_ttm`;
- quality/stability proxy from downside volatility and absolute 20-day return;
- reversal proxy from negative 20-day return;
- low-volatility proxy from 20-day realized volatility;
- liquidity/capacity proxy from 20-day amount and free-float turnover.

No learned weights are used. No post-result sign flip is allowed.

## Controls In Code

- Only current and past price rows are used.
- Daily-basic inputs are joined by same `date`, `asset_id`, and `market`; PIT availability still must be enforced by upstream input construction.
- Low-liquidity names are masked through 20-day amount cross-sectional rank.
- Extreme one-day return rows are masked.
- Unknown factor names are rejected.
- The regime-conditioned variant uses lagged/current market return history and blocks hostile market-momentum windows without deleting coverage accounting requirements.

## Project Integration

The new source is registered in:

- `src/quant_robot/research/pipeline.py`
- `src/quant_robot/experiments/runner.py`
- `src/quant_robot/audit/project_audit.py`

The candidate plan remains:

`configs/family_rotation_seed_round227_public_method_family_rotation_20260624.json`

The family candidates remain:

`configs/family_rotation_candidates_round227_public_method_family_rotation_20260624.json`

## Verification

Passed:

```powershell
python -m unittest tests.unit.test_daily_basic_public_anomaly_residual_ensemble_factors tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_computes_only_requested_daily_basic_public_anomaly_ensemble_factor tests.unit.test_experiment_runner.ExperimentRunnerTests.test_experiment_grid_can_precompute_daily_basic_public_anomaly_ensemble_matrix_once tests.unit.test_project_audit.ProjectAuditTests.test_audit_accepts_registered_daily_basic_public_anomaly_ensemble_factor_source
```

Result:

- 9 tests passed.
- Factor schema and registered names verified.
- Direction sanity test passed.
- Low-liquidity masking verified.
- No-future-row stability verified.
- Pipeline, experiment runner, and project audit integration verified.

## Decision

Promotable profitable factors from Round228: 0.

Paper-ready factors from Round228: 0.

Useful result: 4 pre-registered, computable public-anomaly ensemble factors are now available for long-cycle residual screening.

## Next Direction

Round229 should run a long-cycle residual IC/shape prescreen for the four factors:

`round229_public_anomaly_residual_ensemble_long_cycle_residual_prescreen`

Required gates before any portfolio work:

- full 2015-2025 sample;
- execution lag >= 1;
- tradeability mask exposure audit;
- industry/style residual IC;
- source family correlation dedup;
- FDR or equivalent multiple-testing control;
- signal-window China regime coverage;
- no 2026 final holdout tuning.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
