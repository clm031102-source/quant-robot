# Round112 Market Residual Lead Exposure Dedup Design

## Goal

Audit the Round111 lead `beta_adjusted_range_contraction_60` before any portfolio grid or promotion claim.

The audit must decide whether the lead is a distinct tradable research signal or just another expression of the existing low-volatility/range-contraction cluster. It must also explain the material 2015 IC failure observed in Round111.

## Context

- Machine/task: `office_desktop` / `factor_validation`.
- Market/asset: CN stock only.
- Source audit: `docs/research/cn_stock_market_residual_risk_premia_prescreen_round111_2026-06-22.md`.
- Next direction from startup gate: `round112_market_residual_lead_exposure_dedup`.
- Final holdout: 2026 data remains excluded.
- Promotion remains blocked until cost, capacity, regime, and walk-forward gates pass.

## Design

Create a focused Round112 operation:

- `src/quant_robot/ops/market_residual_lead_exposure_dedup.py`
- `scripts/run_market_residual_lead_exposure_dedup.py`

The operation will reuse existing factor generation instead of creating a new factor family:

- Generate only the Round111 lead through `compute_market_residual_risk_premia_factors`.
- Generate a compact reference set from the existing capacity-safe price-volume cluster:
  - `range_contraction_lowvol_reversal_20`
  - `bollinger_reversal_lowvol_liquid_20`
  - `donchian_pullback_lowvol_liquid_20`
  - `pv_lowvol_reversal_blend_20`
- Compute forward returns with the existing signal-date label helper.
- Run same-date cross-sectional Spearman diagnostics only; no full-period normalization.

## Required Outputs

The result object and output pack must contain:

- `market_residual_lead_exposure_dedup.json`
- `market_residual_lead_exposure_dedup.md`
- `market_residual_lead_reference_correlations.csv`
- `market_residual_lead_exposure_correlations.csv`
- `market_residual_lead_yearly_ic.csv`
- `market_residual_lead_monthly_ic.csv`
- `market_residual_lead_ic_observations.csv`

## Gate Rules

Promotion must stay false. Portfolio grid must stay false.

Hard blockers:

- Prescreen lead evidence missing.
- Lead factor frame missing or empty.
- High reference-factor redundancy.
- Material 2015 regime failure.
- Yearly IC instability.
- High market beta, downside beta, market correlation, residual volatility, or liquidity exposure requiring neutralization.

The next direction after Round112 must route to a three-round review, because rounds 110-112 complete a governed three-round block.

## Success Criteria

Round112 succeeds if it produces a reproducible audit pack that answers:

1. Does the lead remain unique versus the old price-volume/range-contraction cluster?
2. Is the 2015 failure real and material?
3. Are market beta, downside beta, market correlation, volatility, or liquidity exposures large enough to block promotion?
4. Is the next action review/rotate/bridge, with no direct TopN portfolio grid?

## Self Review

- No placeholder requirements.
- Scope is one focused audit, not a new mining family.
- The design preserves final-holdout isolation.
- The design respects the user risk preference: drawdown alone is not a hard rejection, but capacity, exposure, and instability remain hard gates.
