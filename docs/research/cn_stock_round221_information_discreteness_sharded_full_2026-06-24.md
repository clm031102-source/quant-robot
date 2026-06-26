# CN Stock Round221 Information Discreteness Sharded Full Audit

Date: 2026-06-24

Scope: CN A-share stock cross-sectional factor research. This is a full 2015-2025 residual IC, yearly-stability, public-reference, and style-exposure audit. It is not ETF rotation, not a portfolio backtest, not a promotion memo, and not live trading.

## Command

```powershell
python scripts\run_information_discreteness_residual_prescreen.py --sharded --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --lookback-calendar-days 120 --forward-calendar-days 30 --sample-every-n-dates 20 --min-cross-section 30 --min-ic-observations 50 --min-signal-date-amount 10000000 --min-industries 2 --min-assets-per-industry 2 --output-dir data\reports\information_discreteness_residual_prescreen_round221_sharded_full_all_20260624
```

Local output directory:

`data/reports/information_discreteness_residual_prescreen_round221_sharded_full_all_20260624/`

## Data Footprint

| Metric | Value |
|---|---:|
| Candidate count | 6 |
| Factor rows | 49,793,955 |
| Industry-neutral rows | 48,000,428 |
| Residual rows | 48,000,428 |
| Label rows | 10,778,441 |
| Bar rows | 10,785,537 |
| Asset count | 5,707 |
| Reference factor rows | 60,387,667 |
| Reference factor count | 9 |
| Residual research leads | 0 |
| Portfolio preflight candidates | 0 |
| Promotion allowed candidates | 0 |

## Result Table

| Factor | Raw IC | Neutral IC | Residual IC | Residual ICIR | Residual t | IC+ | Year Failures | Ref High | Exposure High | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fip_smooth_momentum_skip5_60` | -0.0164 | -0.0133 | 0.0141 | 0.193 | 9.867 | 58.5% | 1 | 0 | 2 | reject |
| `fip_smooth_pullback_resilience_60_20` | -0.0101 | -0.0077 | 0.0121 | 0.180 | 9.187 | 57.7% | 2 | 0 | 2 | reject |
| `fip_discrete_jump_reversal_20_5` | 0.0496 | 0.0436 | 0.0086 | 0.125 | 6.425 | 53.6% | 3 | 0 | 2 | reject |
| `fip_volume_confirmed_smooth_trend_20_60` | -0.0469 | -0.0389 | 0.0081 | 0.107 | 5.479 | 54.2% | 4 | 0 | 3 | reject |
| `fip_smooth_momentum_quality_60_20` | -0.0263 | -0.0224 | 0.0062 | 0.090 | 4.612 | 54.7% | 2 | 0 | 2 | reject |
| `fip_continuous_accumulation_low_jump_20_60` | -0.0455 | -0.0396 | -0.0041 | -0.060 | -3.071 | 48.0% | 8 | 0 | 2 | reject |

Promotion gate reference: residual mean absolute IC must be at least 0.02, residual ICIR must be at least 0.5, and the factor must not be dominated by size, liquidity, or volatility exposure. None of the six candidates came close after residualization.

## Blocker Histogram

| Count | Blocker |
|---:|---|
| 6 | `candidate_high_size_liquidity_or_volatility_exposure` |
| 6 | `residual_mean_ic_below_threshold` |
| 6 | `residual_icir_below_threshold` |
| 6 | `residual_yearly_ic_instability` |
| 5 | `industry_neutral_yearly_ic_instability` |
| 5 | `raw_yearly_ic_instability` |
| 5 | `industry_neutral_icir_below_threshold` |
| 5 | `industry_neutral_positive_ic_rate_below_threshold` |
| 5 | `industry_neutral_mean_ic_below_threshold` |
| 4 | `residual_positive_ic_rate_below_threshold` |

## Yearly Failure Read

The key failure is not a single weak year. It is instability across several regimes:

- 2015 is a hard stress year. Five of six candidates failed in 2015 or showed negative residual IC around that period.
- `fip_continuous_accumulation_low_jump_20_60` failed 8 yearly checks and is directionally unusable.
- `fip_volume_confirmed_smooth_trend_20_60` failed 2015, 2016, 2023, and 2025.
- `fip_discrete_jump_reversal_20_5` failed 2016, 2017, and 2023 despite having strong raw IC.
- The better-looking residual candidates still failed because their residual IC and ICIR are too small to justify any portfolio conversion.

This means the family is regime-sensitive and style-contaminated. It is not a stable standalone alpha family.

## Reference And Exposure Audit

No candidate was highly redundant with the public reference factors by the configured hard threshold, but several had meaningful overlap with known price-location and reversal references:

- `fip_discrete_jump_reversal_20_5` had max correlation 0.604 with `donchian_position_20`.
- `fip_discrete_jump_reversal_20_5` had max correlation 0.531 with `bollinger_reversal_20`.
- Several candidates had moderate overlap with smart-money, SuperTrend, Bollinger, and Donchian references.

The more serious issue is style exposure:

- `fip_continuous_accumulation_low_jump_20_60` had max exposure 0.982 to `return_20`.
- `fip_smooth_momentum_skip5_60` had max exposure 0.979 to `realized_vol_20` and 0.974 to `return_20`.
- `fip_smooth_momentum_quality_60_20` had max exposure 0.974 to `realized_vol_20` and 0.972 to `return_20`.
- `fip_volume_confirmed_smooth_trend_20_60` had max exposure 0.899 to `amount_trend_20_60`.

So the apparent signal is mostly a repackaged trend, volatility, or liquidity state after full-cycle controls.

## Decision

Round221 produced one useful negative result and no usable factor:

- Research leads: 0.
- Portfolio preflight candidates: 0.
- Promotion candidates: 0.
- Paper-ready candidates: 0.
- Manual/live candidates: 0.

Hard rejects:

- Do not tune FIP windows after this full-sample failure.
- Do not run TopN or cost/capacity grids for the six candidates.
- Do not use the Q2 smoke or short-window result as profit evidence.
- Do not continue the information-discreteness family without a new orthogonal mechanism and a new preregistration.

Next direction:

`round222_rotate_after_information_discreteness_residual_failure`

## Process Lesson

The sharded full-sample path worked and should remain the default for new families. The right optimization is not shorter samples. The right optimization is:

- preregister a public or structural mechanism;
- run a cheap coverage/smoke check only for data readiness;
- then run the same frozen parameters through the 2015-2025 residual screen;
- stop the family immediately when residual IC, yearly stability, and exposure gates all fail.

Safety: research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
