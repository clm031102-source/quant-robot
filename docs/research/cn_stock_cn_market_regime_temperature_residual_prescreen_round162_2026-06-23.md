# CN Market Regime Temperature Residual Prescreen Round162

Date: 2026-06-23

## Scope

Round162 evaluated the 6 pre-registered CN market-regime-temperature candidates from Round161 on the long CN stock sample.

Data window:

- Bars: 2015-01-01 through 2025-12-31
- Factor rows: 20,040,682
- Industry-neutral rows: 19,313,978
- Residual rows: 19,207,569
- Label rows: 10,751,318
- Horizon: 5 trading days
- Execution lag: 1 trading day

## Result

- Candidates tested: 6
- Residual research leads: 0
- Portfolio grid candidates: 0
- Promotion candidates: 0
- Next direction: `round163_rotate_after_china_market_regime_temperature_residual_prescreen_failure`

## Candidate Metrics

| Factor | Raw IC | Neutral IC | Residual IC | Residual ICIR | IC+ | Main blockers |
|---|---:|---:|---:|---:|---:|---|
| `regime_cold_liquidity_reversal_quality_20_5` | 0.0538 | 0.0513 | 0.0289 | 0.328 | 60.0% | 2024 residual failure; high return_20 exposure |
| `index_location_low_residual_value_liquidity_60_10` | 0.0197 | 0.0113 | 0.0254 | 0.217 | 56.4% | weak neutral IC; 2023 sparse negative; high liquidity exposure |
| `dispersion_high_lowvol_residual_reversal_20_5` | 0.0471 | 0.0491 | 0.0172 | 0.177 | 58.9% | residual IC below threshold; state coverage weak; style exposure |
| `regime_hot_turnover_exhaustion_avoidance_10_5` | 0.0144 | 0.0180 | 0.0157 | 0.238 | 60.3% | neutral IC below threshold; residual mean below threshold; 2024 failure |
| `market_temperature_state_interaction_composite_20_5` | 0.0155 | 0.0179 | 0.0141 | 0.180 | 56.0% | weak neutral/residual IC; yearly instability; style exposure |
| `breadth_recovery_residual_momentum_20_10` | -0.0351 | -0.0292 | 0.0071 | 0.085 | 54.4% | weak IC; yearly instability; reference redundancy; style exposure |

## Interpretation

This family improved process quality but did not produce a promotable factor.

The strongest line, `regime_cold_liquidity_reversal_quality_20_5`, is not empty: residual IC 0.0289, residual ICIR 0.328, and residual positive IC rate 60.0%. However, it fails the gate because:

- 2024 residual IC is slightly negative (-0.0031);
- the signal is highly exposed to 20-day return, with mean correlation -0.9365;
- the current form is therefore closer to a regime-conditioned reversal exposure than a clean standalone alpha.

The second notable line, `index_location_low_residual_value_liquidity_60_10`, has residual IC 0.0254 and ICIR 0.217, but its industry-neutral IC is weak and it has high liquidity exposure. It should not be promoted or converted into a portfolio grid.

## Decision

Do not run portfolio conversion, cost-capacity walk-forward, or promotion gates for this family.

Acceptable future use:

- treat cold-liquidity reversal as a diagnostic observation;
- only revisit it through a new pre-registered decomposition that explicitly removes the `return_20` exposure and stress-tests 2024;
- otherwise rotate to a new mechanism after the required Round160-162 three-round review.

## Artifacts

- Tool: `src/quant_robot/ops/cn_market_regime_temperature_residual_prescreen.py`
- CLI: `scripts/run_cn_market_regime_temperature_residual_prescreen.py`
- Tests: `tests/unit/test_cn_market_regime_temperature_residual_prescreen.py`, `tests/unit/test_cn_market_regime_temperature_residual_prescreen_cli.py`
- Local output: `data/reports/cn_market_regime_temperature_residual_prescreen_round162_20260623`

