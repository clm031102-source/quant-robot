# CN Stock External Margin Credit Neutral Dedup Round193

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional factor audit, not ETF rotation
- Input evidence: Round192 margin-credit IC/quantile/turnover prescreen
- Output artifacts: `data/reports/round193_external_margin_credit_neutral_dedup_20260623/`

## Objective

Round192 found two statistically positive margin-credit seeds, but both failed quantile monotonicity. Round193 tested whether those signals had independent alpha after reference-factor deduplication and style residualization, before any portfolio grid or walk-forward conversion.

This round intentionally did not tune direction, window, top-N, cost, or holding parameters after seeing Round192.

## Data And Method

- Bars: 10,785,537 rows, 5,707 CN stock assets, 2015-01-05 to 2025-12-31.
- External margin detail: 1,414,557 rows, 4,660 assets, raw dates 2024-07-01 to 2025-12-31.
- Margin factor rows: 2,435,482.
- Reference technical factor rows: 100,830,409 across 10 capacity-safe price/volume references.
- Residual factor rows: 2,420,402.
- Forward horizon: 20 trading days, execution lag 1.
- Final holdout: excluded; 2026 remains blocked.
- PIT join: margin uses `available_date`; raw margin date must be before signal date.

Reference-correlation sampling was fixed during this round: reference factors are now filtered to the sampled lead dates instead of sampled independently. The first implementation produced false `insufficient_overlap` rows because the 2015-start reference factor sample and the 2024-start margin factor sample had different date phases.

## Results

Round192 raw prescreen:

- `margin_balance_crowding_reversal_20`: IC 0.0555, ICIR 0.962, positive IC rate 83.8%, monotonicity 0.300.
- `margin_financing_acceleration_exhaustion_20`: IC 0.0341, ICIR 0.472, positive IC rate 66.5%, monotonicity 0.600.

Round193 after style residualization:

| Residual factor | Obs | Mean IC | ICIR | t-stat | IC+ |
|---|---:|---:|---:|---:|---:|
| `margin_financing_acceleration_exhaustion_20__style_residual` | 334 | 0.0024 | 0.045 | 0.83 | 51.5% |
| `margin_balance_crowding_reversal_20__style_residual` | 334 | -0.0005 | -0.011 | -0.20 | 47.0% |

Reference deduplication:

- `margin_financing_acceleration_exhaustion_20` is moderately redundant with `volume_contraction_reversal_lowvol_20`: 71 correlation dates, mean absolute correlation 0.464, max absolute correlation 0.613.
- Other tested reference correlations were below the redundancy threshold.
- Style exposures were not individually classified as high exposure, but the residual IC collapse means the usable predictive component did not survive the combined style-neutral audit.

## Gate Decision

Promotion: blocked.

Portfolio grid: blocked.

Blockers:

- `style_residual_ic_not_material`
- `margin_credit_moderately_redundant_with_price_volume_reference`
- `round192_quantile_monotonicity_blocker_not_cleared`
- `industry_metadata_missing_or_not_pit`
- `portfolio_grid_blocked_before_cost_capacity_walk_forward`
- `requires_china_regime_stress_audit`
- `requires_final_holdout_clearance`

## Conclusion

The margin-credit line should not be advanced to walk-forward or portfolio grid. The apparently strong Round192 raw IC did not survive style residualization: one residual IC is near zero and the other is slightly negative. This strongly suggests the raw signal was mostly a proxy for existing price/volume, liquidity, crowding, or regime effects rather than an independent tradable alpha.

Next action: rotate away from margin-credit continuation. Round194 should preregister a new public-indicator or event/tradeability family with economic rationale before testing, while keeping the same long-cycle/PIT/neutralization discipline.
