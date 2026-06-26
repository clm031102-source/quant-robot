# Round116 Public Alpha101 Reference Exposure Dedup Design

## Goal

Audit the only Round115 research lead, `qlib_alpha158_return_std_position_blend_20` at 5-day horizon, before any portfolio grid or promotion.

## Scope

Round116 is not a new mining expansion. It measures whether the lead is just another version of known price-volume/low-vol/reversal factors or hidden exposure to beta, residual volatility, market correlation, or liquidity.

## Inputs

- Bars: CN stock `processed/bars`, 2015-01-01 to 2025-12-31.
- Prescreen report: `data/reports/public_alpha101_capacity_safe_prescreen_round115_20260622/public_alpha101_capacity_safe_prescreen.json`.
- Lead: `qlib_alpha158_return_std_position_blend_20`.
- Horizon: 5 days.

## Reference Set

Compare against prior capacity-safe price-volume candidates, especially:

- `pv_lowvol_reversal_blend_20`
- `range_contraction_lowvol_reversal_20`
- `bollinger_reversal_lowvol_liquid_20`
- `rsi_reversal_lowvol_liquid_14_20`
- `amount_stability_reversal_5_20`
- `donchian_pullback_lowvol_liquid_20`

## Exposure Set

Merge the lead with market-residual exposure diagnostics:

- `beta_120`
- `downside_beta_120`
- `market_corr_60`
- `residual_vol_60`
- `log_adv20_amount`

## Decision

Promotion remains false. Portfolio grid remains blocked. Since Round114-116 are three post-review rounds, the next direction after Round116 is `round117_round114_116_three_round_review_before_next_action`, regardless of whether the lead survives audit.
