# CN Stock Round221 Preregistration: Information Discreteness Path Quality

Date: 2026-06-24

Scope: CN A-share stock cross-sectional factor research. This is not ETF rotation, not live trading, not a portfolio promotion, and not a Sharpe/return claim.

## Decision

Round220 `industry_leader_lag_residual_diffusion` completed a full 2015-2025 sharded residual prescreen and produced zero residual research leads. The next mining direction rotates to:

`information_discreteness_path_quality`

Next required gate:

`round221_information_discreteness_residual_prescreen`

Registered artifacts:

- `configs/family_rotation_candidates_round221_information_discreteness_20260624.json`
- `configs/family_rotation_seed_round221_information_discreteness_20260624.json`
- `src/quant_robot/factors/information_discreteness.py`
- `src/quant_robot/ops/information_discreteness_residual_prescreen.py`
- `scripts/run_information_discreteness_residual_prescreen.py`
- `tests/unit/test_information_discreteness_factors.py`
- `tests/unit/test_information_discreteness_residual_prescreen.py`
- `tests/unit/test_information_discreteness_residual_prescreen_cli.py`

## Public Source

The family is inspired by the Frog-in-the-Pan / information-discreteness momentum literature:

- Da, Gurun, and Warachka, "Frog in the Pan: Continuous Information and Momentum", Review of Financial Studies, 2014: https://doi.org/10.1093/rfs/hhu003
- SSRN version: https://ssrn.com/abstract=1777988

The implementation is not a verbatim academic replication. It is a CN-stock OHLCV proxy family that separates gradual path-consistent moves from discrete jump-driven moves before any IC or portfolio read.

## Why This Family

The previous failure modes were too concentrated:

- moneyflow-only selection;
- public technical trend-state replay;
- direct profitability-quality formula tuning;
- northbound/margin/valuation paths with weak residual materiality;
- industry leader-lag diffusion that looked interesting on a short smoke window but failed the full residual replay.

This family changes the mechanism. It asks whether the market underreacts to continuous low-salience information flow and whether jump-driven moves should be treated as a different, more visible signal likely to mean-revert.

## Candidate Seed

- `fip_smooth_momentum_quality_60_20`
- `fip_smooth_momentum_skip5_60`
- `fip_continuous_accumulation_low_jump_20_60`
- `fip_discrete_jump_reversal_20_5`
- `fip_smooth_pullback_resilience_60_20`
- `fip_volume_confirmed_smooth_trend_20_60`

These are preregistered candidate names only. They are not promotable factors.

## Implementation Guardrails

- Only current and past OHLCV/amount rows are used.
- Future rows must not change historical factor values.
- Low-liquidity names are masked at the raw factor-source layer.
- `path_smoothness`, `sign_consistency`, and `jump_share` definitions are frozen before any real-data IC read.
- A discrete jump is not allowed to masquerade as smooth momentum quality.
- The family must be de-duplicated against plain momentum, reversal, low volatility, liquidity, RSRS, SuperTrend, Bollinger, Donchian, smart-money trend, and prior public technical references.

## Hard Rejects Before Prescreen

- Plain 60-day momentum rank under a FIP label.
- Plain 20-day reversal rank under a FIP label.
- Any portfolio grid before residual IC shape and reference de-duplication.
- Window or weight tuning after seeing the Round221 residual output.
- Same-day close-to-close execution without next-bar lag.
- Any promotion claim from a short smoke window.

## Required Next Gate

Run full long-cycle residual prescreen on 2015-01-01 through 2025-12-31:

- raw IC;
- industry-neutral IC;
- residual IC after size/liquidity/volatility/own-return controls;
- public reference correlation;
- style exposure correlation;
- yearly IC stability including 2015 and 2025;
- multiple-testing count across all preregistered candidates and horizons.

Portfolio conversion remains blocked until at least one candidate clears the residual/reference gate, then separately clears cost/capacity, walk-forward, regime coverage, and strict statistics.

## Current Status

This round produced a registered factor source and preregistration package. It produced zero profitability evidence so far. The only allowed continuation is:

`round221_information_discreteness_residual_prescreen`
