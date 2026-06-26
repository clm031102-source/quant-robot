# CN Stock Capacity-Safe Price-Volume Prescreen Round102 - 2026-06-22

## Executive Summary

Round102 ran the Round101 pre-registered capacity-safe public price-volume, low-volatility, and reversal candidates through a long-cycle Alphalens-style prescreen.

Scope:

- Machine: `office_desktop`
- Market: CN A-share stocks
- Analysis window: 2015-01-01 through 2025-12-31
- Final holdout: 2026 not included
- Candidate count: 10
- Horizons: 5 and 20 trading days
- Execution lag: 1 trading day
- Minimum signal-date amount: 10,000,000
- Bars: 10,785,537 rows across 5,707 assets
- Factor rows: 100,830,409
- Label rows: 21,417,227
- Aligned factor-label rows: 200,175,023
- Factor-horizon tests: 20
- FDR-significant tests: 17
- Research leads: 1
- Promotion-allowed factors: 0

## Decision

Round102 found one statistical research lead:

- `bollinger_reversal_lowvol_liquid_20`, horizon 20

It is not promotable yet. It must next pass correlation de-duplication, cost/capacity portfolio bridge, long-cycle walk-forward, regime coverage, and holdout discipline.

Round103 should not expand the full price-volume family. It should run:

1. Correlation de-duplication for the Bollinger lead against existing public technical and low-volatility signals.
2. Cost and capacity bridge before any portfolio grid.
3. Three-round review for Rounds 101-103 before any new family expansion.

## Top Result

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Monotonicity | Top quantile turnover | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `bollinger_reversal_lowvol_liquid_20` | 20 | 0.0379 | 0.314 | 16.15 | 61.3% | 0.0184 | 0.800 | 24.8% | yes |

Formula:

```text
0.55*cs_z(bollinger_reversal_20)
+0.25*cs_z(-realized_vol_20)
+0.20*cs_z(log_adv20)
```

Interpretation:

- The signal has a known public technical basis: Bollinger mean reversion.
- Low volatility and liquidity terms make it less likely to be a pure illiquid tail effect.
- The 20-day horizon is stronger than the 5-day horizon.
- The top-minus-bottom quantile spread is positive and quantile monotonicity is acceptable.

Why it is still not promotable:

- This is not a costed portfolio result.
- No correlation de-duplication has been run yet.
- No walk-forward fold acceptance exists yet.
- Regime behavior is unknown.
- Final 2026 holdout remains unread and must stay protected.

## Strong But Blocked Results

Several candidates had strong IC but failed quantile translation.

| Factor | Horizon | IC | ICIR | Q5-Q1 | Monotonicity | Main blocker |
|---|---:|---:|---:|---:|---:|---|
| `range_contraction_lowvol_reversal_20` | 20 | 0.0973 | 0.615 | 0.0357 | 0.300 | weak quantile monotonicity |
| `pv_lowvol_reversal_blend_20` | 20 | 0.0790 | 0.683 | -0.0089 | -0.300 | top quantile underperformed bottom quantile |
| `range_contraction_lowvol_reversal_20` | 5 | 0.0773 | 0.501 | 0.0184 | 0.500 | weak quantile monotonicity |
| `volume_contraction_reversal_lowvol_20` | 20 | 0.0576 | 0.479 | -0.0180 | -0.100 | top quantile underperformed bottom quantile |
| `price_volume_trend_quality_20_60` | 20 | -0.0698 | -0.470 | -0.0477 | -0.400 | direction failed |

These are useful diagnostics, not promotion evidence. High IC did not reliably translate into a clean top-quantile long signal.

## User Risk Tolerance Update

The user clarified that around 30% drawdown can be acceptable when total return and annualized return are strong.

Policy update:

- A drawdown under roughly 30% should not be a single-name hard rejection by itself.
- Capacity, tradability, extreme-trade flags, cost, and execution remain hard gates.
- High-return low-turnover lines should be treated as research leads only when the capacity-clean version keeps enough return quality.

This matters for prior `turnover_rate_low` and `turnover_rate_f_low` near-misses. Their headline return and Sharpe were attractive, but the capacity-clean large-market-value versions collapsed to weak overlap-adjusted Sharpe. That is a capacity/tradability failure, not just a drawdown preference issue.

## Engineering Result

The first real run exposed an implementation bottleneck: an all-factor merge and groupby attempted to allocate about 6.4 GB during sorting.

Fix:

- Added a streaming per-factor/per-horizon summarizer.
- Added a regression test that fails if the summarizer attempts an all-factor merge.
- Re-ran the full 2015-2025 prescreen successfully after the fix.

Output files were written under:

```text
data/reports/capacity_safe_price_volume_prescreen_round102_20260622/
```

These generated data/report outputs stay out of Git by policy.

## Next Direction

Set startup gate next direction to:

```text
round103_capacity_safe_price_volume_bollinger_lead_dedup_and_three_round_review
```

Blocked follow-ups:

- No full-family parameter expansion from `range_contraction_lowvol_reversal_20` before monotonicity is repaired.
- No positive-direction continuation for `price_volume_trend_quality_20_60` after negative IC.
- No direct promotion of `pv_lowvol_reversal_blend_20` before top-minus-bottom quantile translation is fixed.
- No drawdown-tolerance waiver for capacity or tradability failures.

