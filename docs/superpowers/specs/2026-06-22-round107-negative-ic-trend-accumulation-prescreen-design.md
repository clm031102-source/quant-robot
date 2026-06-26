# Round107 Negative-IC Trend Accumulation Prescreen Design

## Context

Round105 showed the positive trend/amount accumulation family had strong negative IC on the 2015-2025 CN stock long-cycle replay. Round106 converted that evidence into 10 pre-registered anti-overheat hypotheses, explicitly marking the Round105 result as hypothesis evidence rather than promotion evidence.

The user clarified that a drawdown near 30 percent can be acceptable when return quality is strong. This does not waive capacity, tradeability, cost, lookahead, multiple-testing, or sample-stability gates.

## Goal

Build Round107 as a long-cycle Alphalens-style prescreen for the 10 Round106 negative-IC trend/amount candidates. The output can only create research leads. It cannot promote a factor, run portfolio grids, or use the 2026 final holdout.

## Scope

Round107 will:

- Reuse the Round105 CN stock bars loader, long-cycle window, forward-return labels, IC, quintile, turnover, and FDR summary code.
- Reuse the Round105 feature matrix so positive and inverse directions are directly comparable.
- Compute exactly the 10 Round106 pre-registered candidates.
- Apply the same capacity mask: signal-date amount, adv20 amount, and extreme daily return guard.
- Write JSON, Markdown, result CSV, and IC-observation CSV reports under `data/reports`.
- Keep promotion disabled and require correlation de-duplication before any portfolio grid.

Round107 will not:

- Tune windows or weights after seeing Round105 or Round107 results.
- Read 2026 final holdout by default.
- Treat high raw return or tolerable drawdown as a capacity waiver.
- Promote any candidate directly to paper-ready or live use.

## Candidate Formula Mapping

All formulas are `higher_is_better` and use cross-sectional z-scored Round105 features:

- `anti_volume_weighted_momentum_quality_20`: `-0.50*z_volume_weighted_return_20 -0.30*z_return_efficiency_20 +0.20*z_log_adv20`
- `anti_money_pressure_efficiency_20`: `-0.55*z_money_pressure_20 -0.25*z_return_efficiency_20 +0.20*z_log_adv20`
- `anti_accumulation_distribution_pressure_20`: `-0.50*z_accumulation_distribution_20 -0.30*z_momentum_20 +0.20*z_log_adv20`
- `anti_turnover_expansion_momentum_10_40`: `-0.45*z_momentum_20 -0.35*z_amount_expansion_10_40 +0.20*z_log_adv20`
- `anti_amount_accumulation_breakout_20_60`: `-0.45*z_price_breakout_20 -0.35*z_amount_trend_20_60 +0.20*z_log_adv20`
- `anti_obv_late_accumulation_20`: `-0.50*z_obv_slope_20 -0.30*z_momentum_20 +0.20*z_log_adv20`
- `overheat_avoidance_high_volume_breakout_20`: `-0.45*z_close_to_20d_high -0.35*z_amount_zscore_20 +0.20*z_return_efficiency_20`
- `overheat_avoidance_relative_strength_60`: `-0.55*z_momentum_60 -0.25*z_amount_percentile_60 +0.20*z_log_adv20`
- `amount_exhaustion_pullback_20_60`: `-0.40*z_amount_trend_20_60 -0.35*z_price_breakout_20 +0.25*z_log_adv20`
- `overheat_avoidance_composite_20_60`: `-0.25*z_money_pressure_20 -0.25*z_accumulation_distribution_20 -0.25*z_momentum_60 -0.15*z_amount_trend_20_60 +0.10*z_log_adv20`

## Gates

A candidate can become a Round107 research lead only if the existing prescreen gate marks it as FDR-significant with positive IC, sufficient ICIR, positive IC rate, positive Q5-Q1 spread, adequate monotonicity, and acceptable top-quantile turnover.

If no research lead survives, the next direction must rotate away from this family rather than tune the same formulas. If one or more leads survive, the next direction is correlation de-duplication before any portfolio grid.

## Verification

Verification requires:

- Unit tests for factor generation, holdout exclusion, promotion blocking, and CLI output files.
- RED verification before implementation.
- GREEN verification after implementation.
- A real long-cycle run on `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260616_combined_research`.
- Startup gate update and project audit after report generation.
