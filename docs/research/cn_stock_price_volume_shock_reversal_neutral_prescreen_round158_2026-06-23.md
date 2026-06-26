# CN Stock Price-Volume Shock Reversal Neutral Prescreen Round158

## Summary

- Stage: `price_volume_shock_reversal_neutral_prescreen`
- Market/scope: CN A-share stocks only
- Window: 2015-01-05 to 2025-12-31
- Bar rows: 10,785,537
- Assets: 5,707
- Candidate count: 8
- Test count: 8
- Factor rows: 80,710,820
- Industry-neutral rows: 77,787,758
- Residual rows: 77,543,727
- Horizon: 5 trading days
- Execution lag: 1 trading day
- Residual research leads: 0
- Portfolio grid allowed candidates: 0
- Promotion allowed candidates: 0
- Next direction: `round159_rotate_after_price_volume_shock_reversal_neutral_prescreen_failure`

## Result Table

| Factor | Raw IC | Raw ICIR | Industry-neutral IC | Residual IC | Residual ICIR | Ref high | Exposure high | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `amihud_shock_reversal_liquid_20_60` | 0.0224 | 0.191 | 0.0193 | 0.0174 | 0.247 | 1 | 2 | reject |
| `downside_volume_absorption_reversal_10_60` | 0.0348 | 0.298 | 0.0343 | 0.0150 | 0.219 | 0 | 1 | reject |
| `volatility_compression_after_shock_reversal_20_60` | -0.0286 | -0.289 | -0.0264 | -0.0100 | -0.185 | 2 | 3 | reject |
| `range_expansion_exhaustion_reversal_20` | -0.0297 | -0.261 | -0.0245 | 0.0075 | 0.121 | 0 | 0 | reject |
| `gap_range_failure_reversal_5_20` | -0.0300 | -0.246 | -0.0231 | 0.0069 | 0.081 | 1 | 2 | reject |
| `volume_climax_reversal_close_location_20` | -0.0067 | -0.074 | -0.0069 | 0.0059 | 0.093 | 0 | 0 | reject |
| `low_liquidity_stress_normalization_20_60` | 0.0053 | 0.049 | 0.0010 | 0.0053 | 0.075 | 0 | 2 | reject |
| `vwap_proxy_reclaim_reversal_20` | -0.0097 | -0.090 | -0.0093 | 0.0005 | 0.007 | 0 | 0 | reject |

## What Failed

The family produced some raw IC, but the signal did not survive the gates that matter for a tradable CN stock factor.

- `downside_volume_absorption_reversal_10_60` had the strongest raw IC at 0.0348 and industry-neutral IC at 0.0343, but residual IC fell to 0.0150, below the 0.02 threshold, and it retained high return exposure.
- `amihud_shock_reversal_liquid_20_60` had raw IC 0.0224, but industry-neutral IC dropped below threshold, residual IC stayed below threshold, and it was both reference-redundant and style-exposed.
- Several candidates had negative raw IC, which means the preregistered direction was wrong rather than merely weak.
- All candidates had residual yearly instability; this blocks promotion even when the average residual IC is positive.

## Decision

Do not tune this family further. The correct action is to rotate in Round159 rather than expand windows, thresholds, or TopN grids. Price-volume shock reversal may contain a weak effect, but it is not independent enough after industry/style neutralization to justify portfolio work.

Blocked follow-ups:

- `price_volume_shock_reversal_portfolio_grid_after_zero_residual_leads`
- `price_volume_shock_reversal_parameter_tuning_after_round158_zero_residual_leads`
- `amihud_or_downside_absorption_direct_promotion_after_subthreshold_residual_ic`
- `vwap_proxy_or_gap_range_failure_inversion_without_new_preregistration`

## Round159 Direction

Rotate away from this family. The next family should not be RSRS, moneyflow-only, or price-volume shock parameter tuning. A better Round159 direction is a genuinely different mechanism, such as PIT financial/event coverage repair, cross-sectional quality/value with strict announcement-date lag, or another public-method family with a new economic thesis and preregistered neutral prescreen.
