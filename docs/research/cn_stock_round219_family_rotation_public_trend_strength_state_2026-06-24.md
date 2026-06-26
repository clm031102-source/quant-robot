# CN Stock Round219 Family Rotation: Public Trend-Strength State

Date: 2026-06-24

Scope: CN stock cross-sectional factor mining. This is not ETF rotation, not live trading, and not a profitability claim.

## Decision

Round218 optimized the startup/method controls after the Round217 PIT profitability-quality screen found zero FDR leads. The next mining direction is now:

`round219_public_trend_strength_state_preregistration`

Selected family:

`public_trend_strength_state_residual`

The generated rotation evidence is stored locally under:

`data/reports/cn_stock_family_rotation_decision_round219_public_trend_strength_state_20260624/`

That local report reviewed 7 factor families:

- 1 selected for preregistration.
- 5 hibernated.
- 1 retained only as a control/mask.
- 0 data-gap families.
- 0 blockers.

## Why This Family

The previous work failed because several branches kept optimizing within already-damaged directions:

- Direct PIT profitability-quality tuning had 14 candidates, 28 controlled IC tests, 1204 IC observations, and zero FDR leads in Round217.
- Standalone valuation reversion had raw IC but collapsed after industry/style residualization in Round212.
- Northbound/external crowding had weak or unstable IC shape and zero long-cycle leads.
- RSRS, SuperTrend, 52-week, and Donchian-style public technical variants previously showed raw pockets but failed residual/de-dup or costed walk-forward gates.
- Tradeability/limit-event structure is important, but it is a risk/control layer, not a standalone alpha family.

Round219 therefore rotates to public trend-strength and market-state formulas that were not the prior RSRS/SuperTrend/52-week replay. The point is not to blindly buy high ADX or KAMA names. The point is to test whether lagged trend-strength, trend-efficiency, and range-state variables can condition residual cross-sectional stock selection after tradeability, industry/style, regime, and multiple-testing controls.

## Candidate Seed

The preregistered candidate ideas are:

- `adx_trend_strength_exhaustion_reversal_14_20`
- `adx_choppiness_mean_reversion_quality_14_20`
- `kama_efficiency_trend_decay_10_30`
- `aroon_range_exhaustion_reversal_25_20`
- `williams_range_failure_reversal_14_20`
- `trend_strength_state_residual_composite_20`

These names are seeds only. They are not promotable factors and should not be run through a portfolio grid before the residual IC/shape/dedup gate.

## Mandatory Controls

Before any Round219 factor can claim research value, it must pass:

- Public formula source registration.
- No same-day or forward-label leakage.
- A-share tradeability masks.
- Industry/style residual evaluation.
- Reference de-duplication against RSRS, SuperTrend, Bollinger, and Donchian families.
- Multiple-testing accounting.
- Full-sample long-cycle IC shape screen before portfolio grid.
- China regime coverage.

## Startup Protocol Update

Updated:

- `configs/factor_mining_startup_cn_stock.json`
- `configs/family_rotation_candidates_round219_public_trend_strength_state_20260624.json`
- `configs/family_rotation_seed_round219_public_trend_strength_state_20260624.json`
- `src/quant_robot/factors/public_trend_strength_state.py`
- `src/quant_robot/research/pipeline.py`

The default startup protocol now points to this report and the Round219 preregistration direction. It also records that portfolio grid, Sharpe ranking, promotion, and live claims remain blocked until residual IC shape, de-duplication, long-cycle replay, walk-forward, cost/capacity, and regime checks clear.

## Implementation Update

The first reusable Round219 implementation landed as a separate factor source:

`public_trend_strength_state`

Registered factor names:

- `adx_trend_strength_exhaustion_reversal_14_20`
- `adx_choppiness_mean_reversion_quality_14_20`
- `kama_efficiency_trend_decay_10_30`
- `aroon_range_exhaustion_reversal_25_20`
- `williams_range_failure_reversal_14_20`
- `trend_strength_state_residual_composite_20`

The implementation intentionally keeps this family separate from the older `public_technical`, `public_trend_volume`, RSRS, and SuperTrend paths so family-level audit and hibernation decisions remain clean.

Controls covered at implementation level:

- Only current and past OHLCV rows are used.
- Unsupported factor names are rejected.
- Low-liquidity/extreme-day masking exists at the raw factor-source layer.
- The research pipeline accepts `factor_source=public_trend_strength_state`.

## Residual Prescreen Update

The long-cycle residual prescreen has now been run on 2015-01-05 through 2025-12-31 CN stock data:

- Data window: 5,707 assets, 10,785,537 bar rows, 10,751,318 label rows.
- Candidate tests: 6 factor names x 5-day horizon.
- Factor rows: 47,693,243.
- Industry-neutral rows: 45,952,010.
- Residual rows: 45,952,010.
- Reference families checked: 9 public technical references.
- Residual research leads: 0.
- Portfolio-grid allowed candidates: 0.
- Promotion allowed candidates: 0.

The output artifacts are stored locally under:

`data/reports/public_trend_strength_state_residual_prescreen_round219_20260624/`

Best residual IC values were still below gate:

- `aroon_range_exhaustion_reversal_25_20`: raw IC 0.0443, industry-neutral IC 0.0390, residual IC 0.0120, residual ICIR 0.210.
- `trend_strength_state_residual_composite_20`: raw IC 0.0522, industry-neutral IC 0.0473, residual IC 0.0118, residual ICIR 0.175.
- `adx_trend_strength_exhaustion_reversal_14_20`: residual IC 0.0099, residual ICIR 0.189, with industry-neutral and exposure blockers.

Primary blockers:

- 6/6 candidates failed residual mean IC threshold.
- 6/6 candidates failed residual yearly stability.
- 5/6 candidates had high size/liquidity/volatility exposure.
- 5/6 candidates failed residual ICIR threshold.

This result rejects the public trend-strength-state family for continuation. No TopN portfolio grid, Sharpe ranking, annual return, win-rate, or promotion conclusion is allowed from this family.

Engineering note: the full-window run succeeded but was heavy, peaking above 30GB process memory. The next process optimization should cache/reuse long-cycle factor, reference, and exposure matrices or run yearly shards before residual aggregation.

## Result Status

This round produced a reusable process improvement, one selected factor family direction, six implemented/preregistered factor names, and a completed long-cycle residual/redundancy audit. It produced no profitable factor and no paper-ready signal.

Next allowed action:

`round220_rotate_after_public_trend_strength_state_residual_prescreen_failure`
