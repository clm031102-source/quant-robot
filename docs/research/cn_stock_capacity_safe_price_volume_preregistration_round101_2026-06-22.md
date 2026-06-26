# CN Stock Capacity-Safe Price-Volume Preregistration Round101 - 2026-06-22

## Executive Summary

Round101 completed the post-Round100 family rotation. The office desktop did not run another blind portfolio grid. It pre-registered a new capacity-safe public price-volume, low-volatility, and reversal composite family for CN A-share stock research.

Result:

- Pre-registered candidates: 10
- Unique candidate names: 10
- Blockers: 0
- Portfolio-backtest-allowed candidates: 0
- Promotion-allowed candidates: 0
- Next required gate: `alphalens_style_ic_quantile_turnover_prescreen`
- Live boundary allowed: false

## Candidate List

| Factor | Family | Windows | Public references | Next gate |
|---|---|---|---|---|
| `pv_lowvol_reversal_blend_20` | price-volume low-vol reversal | 5, 20 | Alphalens, WorldQuant 101 Alphas, qlib | IC/quantile/turnover prescreen |
| `range_contraction_lowvol_reversal_20` | range contraction | 5, 20 | Alphalens, VectorBT, qlib | IC/quantile/turnover prescreen |
| `volume_contraction_reversal_lowvol_20` | volume contraction | 5, 20 | Alphalens, WorldQuant 101 Alphas, PyFolio | IC/quantile/turnover prescreen |
| `price_volume_trend_quality_20_60` | trend quality | 20, 60 | qlib, Alphalens, VectorBT | IC/quantile/turnover prescreen |
| `skip5_momentum_lowvol_20` | momentum low-vol | 5, 20 | qlib, Alphalens, PyFolio | IC/quantile/turnover prescreen |
| `pv_corr_reversal_capacity_safe_20` | price-volume divergence | 20 | WorldQuant 101 Alphas, Alphalens, PyFolio | IC/quantile/turnover prescreen |
| `bollinger_reversal_lowvol_liquid_20` | public technical reversal | 20 | VectorBT, Alphalens, PyFolio | IC/quantile/turnover prescreen |
| `rsi_reversal_lowvol_liquid_14_20` | public technical reversal | 14, 20 | VectorBT, Alphalens, qlib | IC/quantile/turnover prescreen |
| `amount_stability_reversal_5_20` | liquidity capacity | 5, 20 | Alphalens, PyFolio, qlib | IC/quantile/turnover prescreen |
| `donchian_pullback_lowvol_liquid_20` | public technical pullback | 20 | VectorBT, Alphalens, WorldQuant 101 Alphas | IC/quantile/turnover prescreen |

## Capacity And Safety Policy

Every candidate carries the same minimum execution discipline:

- exclude ST names
- exclude suspended names
- exclude untradable limit-up/limit-down names
- minimum listing age: 120 days
- minimum signal-date amount: 10,000,000
- maximum position ADV participation: 5%
- require calendar holding gate

This was added because prior near-misses were repeatedly killed by capacity, participation, or drawdown after apparently attractive raw returns.

## Why This Direction

The previous profitability-quality family had clean PIT data but failed the controlled IC screen after multiple-testing accounting. Continuing to tune that family would be low expected value.

The new family follows public research tooling discipline:

- Alphalens-style IC and quantile diagnostics before portfolio construction.
- VectorBT/PyFolio-style later portfolio/risk review only after statistical leads exist.
- WorldQuant/qlib style formula inspiration, but no random expression mining without a public rationale.

## Decision

Round101 is passed as a preregistration round only. It produces 10 research candidates and 0 tradable or promotable factors.

Round102 must build the factor matrix and run the Alphalens-style IC, quantile, turnover, coverage, and capacity prescreen. Direct top-N portfolio grids remain blocked until that screen produces a real statistical lead.
