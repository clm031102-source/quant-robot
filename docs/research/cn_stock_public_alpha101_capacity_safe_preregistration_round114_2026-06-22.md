# CN Stock Public Alpha101 Capacity-Safe Preregistration - Round114

## Summary

Round114 completed a family rotation away from the blocked market-residual standalone line and preregistered 10 curated public Alpha101/Qlib-style CN stock candidates.

- Stage: `public_alpha101_capacity_safe_preregistration`
- Runtime artifact: `data/reports/public_alpha101_capacity_safe_preregistration_round114_20260622`
- Candidate count: 10
- Unique candidate names: 10
- Preregistration blockers: none
- Portfolio backtest allowed: 0
- Promotion allowed: 0
- Live boundary allowed: false
- Next direction: `round115_public_alpha101_ic_quantile_turnover_prescreen`

This round produced no profitable/live-ready factor. It only created a fixed, auditable candidate set for the next IC/quantile/turnover/capacity prescreen.

## Why This Direction

Round110-112 found one statistical lead, `beta_adjusted_range_contraction_60`, but Round112 blocked promotion because of high reference redundancy, high exposure to residual-volatility/market-correlation proxies, a 2015 regime failure, and unstable monthly/yearly evidence. Continuing the same market-residual family would be a bad use of time.

Round114 therefore switches to public formulaic-alpha references, but with two controls:

- No broad random formula search.
- No direct portfolio grid before Round115 prescreen.

Public references used as hypothesis sources:

- `101 Formulaic Alphas`: https://arxiv.org/abs/1601.00991
- Microsoft Qlib: https://github.com/microsoft/qlib
- Existing project gates inspired by Alphalens/vectorbt/pyfolio-style evaluation.

## Registered Candidates

| Factor | Family | Windows | Required fields | Formula template |
|---|---|---:|---|---|
| `alpha101_intraday_close_position_reversal` | public_formula_intraday_reversal | 1,20 | adj_close, open, high, low, amount | `-1.00*cs_z((adj_close-open)/(high-low+1e-6))+0.20*cs_z(log_adv20)` |
| `alpha101_gap_fade_amount_confirmed_5_20` | public_formula_gap_reversal | 5,20 | adj_close, open, amount | `0.60*cs_z(-(open/prev_adj_close-1))+0.25*cs_z(-amount_z_20)+0.15*cs_z(log_adv20)` |
| `alpha101_price_volume_corr_reversal_20` | public_formula_price_volume_corr | 20 | adj_close, amount | `-0.70*cs_z(ts_corr(cs_rank(return_1),cs_rank(amount_return_1),20))+0.30*cs_z(log_adv20)` |
| `alpha101_vwap_proxy_reversion_liquid_20` | public_formula_vwap_reversion | 20 | adj_close, amount, volume | `0.65*cs_z(-(adj_close/vwap_proxy_20-1))+0.35*cs_z(log_adv20)` |
| `alpha101_decay_rank_reversal_10` | public_formula_decay_rank | 5,10 | adj_close, amount | `0.75*cs_z(decay_linear(cs_rank(-return_5),10))+0.25*cs_z(log_adv20)` |
| `alpha101_amount_shock_exhaustion_5_20` | public_formula_amount_exhaustion | 5,20 | adj_close, amount | `0.55*cs_z(-return_5)+0.30*cs_z(-amount_z_20)+0.15*cs_z(log_adv20)` |
| `alpha101_open_close_pressure_fade_10` | public_formula_open_close_pressure | 10 | adj_close, open, amount | `-0.70*cs_z(ts_mean((adj_close-open)/(open+1e-6),10))+0.30*cs_z(log_adv20)` |
| `alpha101_range_compression_liquid_20` | public_formula_range_compression | 20 | adj_close, high, low, amount | `-0.55*cs_z(ts_mean((high-low)/(adj_close+1e-6),20))-0.15*cs_z(realized_vol_20)+0.30*cs_z(log_adv20)` |
| `qlib_alpha158_return_std_position_blend_20` | qlib_alpha158_feature_blend | 5,20 | adj_close, high, low, amount | `0.45*cs_z(-return_5)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(kbar_close_position_20)+0.10*cs_z(log_adv20)` |
| `alpha101_volume_rank_divergence_20` | public_formula_volume_rank_divergence | 5,20 | adj_close, amount | `-0.60*cs_z(ts_corr(cs_rank(adj_close),cs_rank(amount),20))+0.25*cs_z(-return_5)+0.15*cs_z(log_adv20)` |

## Gates Preserved

- 2026 final holdout remains untouched.
- Candidate count is fixed before measurement.
- Every candidate counts toward multiple-testing accounting.
- Portfolio grid is blocked before Round115.
- Promotion is blocked before long-cycle IC, quantile, turnover, cost, capacity, redundancy, and walk-forward evidence.
- User drawdown tolerance does not waive capacity or extreme-trade checks.

## Round115 Required Work

Round115 should build the public Alpha101 translation matrix and run the long-cycle prescreen:

- Data window: 2015-01-01 to 2025-12-31.
- Horizons: 5, 10, 20 days with execution lag.
- Metrics: RankIC, ICIR, t-stat, positive IC rate, quantile monotonicity, quantile spread, factor turnover, coverage, capacity participation, and extreme-trade diagnostics.
- Dedup: compare against prior low-vol/reversal, price-volume, gap, trend, and market-residual reference factors.
- Promotion policy: 0 promotion until at least one candidate survives Round115 and later walk-forward/costed validation.

## Conclusion

Round114 improved the process, not the PnL. It converted a broad public-method idea into 10 fixed, capacity-aware, auditable hypotheses. The correct next move is Round115 prescreen, not more Alpha101 expansion and not portfolio optimization.
