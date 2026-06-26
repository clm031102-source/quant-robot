# CN Stock Public Alpha101 Capacity-Safe Prescreen - Round115

## Summary

Round115 ran the fixed Round114 public Alpha101/Qlib-style candidate set through the full 2015-2025 CN stock long-cycle IC/quantile/turnover/capacity prescreen.

- Runtime artifact: `data/reports/public_alpha101_capacity_safe_prescreen_round115_20260622`
- Bar rows: 10,785,537
- Bar assets: 5,707
- Factor rows: 101,214,674
- Label rows: 32,140,060
- Aligned rows: 301,552,533
- Candidates: 10
- Tests: 30 factor/horizon combinations
- FDR-significant tests: 27
- Research leads: 1
- Promotion allowed: 0
- Next direction: `round116_public_alpha101_reference_exposure_dedup`

This is the first public Alpha101/Qlib-style pass that produced one strict research lead under the current prescreen gate. It is still not a promotable or tradable factor.

## Research Lead

| Factor | Horizon | IC | ICIR | t-stat | IC positive | Q5-Q1 | Monotonicity | Top turnover | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `qlib_alpha158_return_std_position_blend_20` | 5 | 0.0415 | 0.323 | 16.68 | 63.4% | 0.01794 | 0.900 | 34.9% | yes | yes |

Formula:

`0.45*cs_z(-return_5)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(kbar_close_position_20)+0.10*cs_z(log_adv20)`

Interpretation:

This is a compact Qlib Alpha158-style blend: short reversal, low realized volatility, candlestick close-position, and liquidity. It passed the statistical lead gate at 5-day horizon because it had positive IC, positive ICIR, strong t-stat, positive quantile spread, good monotonicity, and acceptable top-quantile turnover.

## Important Non-Leads

Several public formula candidates were statistically significant but failed the stricter lead gate:

- `alpha101_intraday_close_position_reversal`: strong negative IC across 5/10/20 days. This says the registered direction is wrong or the signal is a short/avoidance candidate, not a long-only alpha as written.
- `alpha101_vwap_proxy_reversion_liquid_20`: strong negative IC across horizons. Do not tune it directly; inverse direction would require a new preregistration.
- `alpha101_open_close_pressure_fade_10`: strong negative IC across horizons. Also an inverse-direction candidate only after new preregistration.
- `alpha101_volume_rank_divergence_20`: positive IC and ICIR, but top-minus-bottom quantile spread was negative and monotonicity was weak. This is exactly the IC-to-portfolio gap problem the process is meant to catch.
- `alpha101_range_compression_liquid_20`: low turnover and positive quantile spread, but IC/ICIR too weak.

## Why Promotion Is Still Zero

The sole lead has not passed:

- Reference redundancy vs prior low-vol/reversal/price-volume clusters.
- Exposure diagnostics vs beta, market correlation, residual volatility, size/liquidity.
- Yearly/monthly stability.
- Walk-forward train/test validation.
- Cost and capacity portfolio conversion.
- Regime coverage.
- 2026 final holdout.

So this result is useful, but it is not yet a paper-ready or live-ready factor.

## Decision

Advance to:

`round116_public_alpha101_reference_exposure_dedup`

Round116 should audit `qlib_alpha158_return_std_position_blend_20` against existing reference factors and exposure proxies before any portfolio grid. The inverse-direction Alpha101 failures should be logged as rejected for now, not immediately flipped without preregistration.
