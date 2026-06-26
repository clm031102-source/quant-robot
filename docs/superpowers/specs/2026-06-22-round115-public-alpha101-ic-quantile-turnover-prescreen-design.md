# Round115 Public Alpha101 IC/Quantile/Turnover Prescreen Design

## Goal

Round115 measures the 10 Round114 public Alpha101/Qlib-style candidates on CN stock bars using the long-cycle prescreen gate before any portfolio grid or promotion.

## Scope

Build a dedicated public Alpha101 translation layer because the existing price-volume prescreen loader does not read all fields needed by the Round114 formulas. The new layer reads `open`, `high`, `low`, `adj_close`, `volume`, `amount`, and `vwap` from `processed/bars`, computes the fixed candidates, then reuses the existing IC/quantile/turnover summarizer.

## Candidate Translation

The prescreen must compute exactly the Round114 candidate names:

- `alpha101_intraday_close_position_reversal`
- `alpha101_gap_fade_amount_confirmed_5_20`
- `alpha101_price_volume_corr_reversal_20`
- `alpha101_vwap_proxy_reversion_liquid_20`
- `alpha101_decay_rank_reversal_10`
- `alpha101_amount_shock_exhaustion_5_20`
- `alpha101_open_close_pressure_fade_10`
- `alpha101_range_compression_liquid_20`
- `qlib_alpha158_return_std_position_blend_20`
- `alpha101_volume_rank_divergence_20`

No random formulas and no parameter expansion are allowed in this round.

## Measurement

Use 2015-01-01 to 2025-12-31 by default, with 2026 excluded. Compute forward returns with execution lag and horizons 5/10/20. Preserve capacity gating with minimum same-day amount and ADV20 amount.

## Decision

Round115 may produce research leads only. Promotion remains false. If leads exist, the next action is Alpha101 reference redundancy and exposure dedup. If no leads survive, the next action is family rotation or Round114-116 three-round review after the third post-review round.
