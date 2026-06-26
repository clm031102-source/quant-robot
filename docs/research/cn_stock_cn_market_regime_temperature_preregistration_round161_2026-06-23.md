# CN Market Regime Temperature Preregistration Round161

Date: 2026-06-23

## Scope

Round161 starts a new CN-stock factor family after the Round160 tradeability/limit-event proxy screen produced zero research leads.

This is a preregistration only. It does not claim profitability and does not allow portfolio grids or promotion.

## Result

- Candidates: 6
- Families: 6
- Failed recent family reentry: 0
- Lagged regime required candidates: 6
- Residual prescreen required candidates: 6
- Portfolio candidates: 0
- Promotion candidates: 0
- Next required gate: `round162_china_market_regime_temperature_residual_prescreen`

## Why This Direction

The project had repeatedly spent compute on families that later failed residual, capacity, tradeability, or robustness checks. Round161 uses the new family-rotation decision to force a different mechanism:

- lagged market breadth;
- liquidity and turnover temperature;
- cross-sectional dispersion;
- index-location state;
- state-conditional interaction with stock-level residual signals.

This directly addresses the China-market-regime control gap while avoiding direct reentry into:

- `tradeability_limit_events`
- `price_volume_shock_reversal`
- `public_technical_failure_reversal`
- `pit_profitability_event_revision`
- `industry_relative_strength_breadth_bridge`
- `moneyflow_residual_regime`

## Candidate Parameters

| Factor | Family | Direction | Windows |
|---|---|---|---|
| `regime_cold_liquidity_reversal_quality_20_5` | cold_liquidity_reversal | higher is better | 5, 20, 60 |
| `regime_hot_turnover_exhaustion_avoidance_10_5` | hot_turnover_exhaustion | lower is better | 5, 10, 20 |
| `breadth_recovery_residual_momentum_20_10` | breadth_recovery_momentum | higher is better | 10, 20, 60 |
| `dispersion_high_lowvol_residual_reversal_20_5` | dispersion_reversal | higher is better | 5, 20, 60 |
| `index_location_low_residual_value_liquidity_60_10` | low_index_location_value_liquidity | higher is better | 10, 60, 252 |
| `market_temperature_state_interaction_composite_20_5` | regime_temperature_composite | higher is better | 5, 20, 60, 252 |

## Mandatory Controls

Every candidate must keep:

- lagged market-temperature state;
- no same-day forward-label leakage;
- tradeability filter before signal evaluation;
- industry/style residual evaluation;
- regime coverage by signal window;
- multiple-testing accounting;
- no portfolio grid before residual prescreen.

## Artifacts

- Tool: `src/quant_robot/ops/cn_market_regime_temperature_preregistration.py`
- CLI: `scripts/run_cn_market_regime_temperature_preregistration.py`
- Tests: `tests/unit/test_cn_market_regime_temperature_preregistration.py`, `tests/unit/test_cn_market_regime_temperature_preregistration_cli.py`
- Local output: `data/reports/cn_market_regime_temperature_preregistration_round161_20260623`

