# CN Stock Public Technical Failure-Reversal Neutral Dedup Round156

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock cross-sectional alpha.
- Source prescreen: `docs/research/cn_stock_public_technical_failure_reversal_prescreen_round155_2026-06-23.md`.
- Lead tested: `inverse_rsrs_slope_failure_liquid_18_60`.
- Horizon: 5 trading days, execution lag 1.
- Data window: 2015-01-05 to 2025-12-31.
- Final holdout: not included.
- Stage: neutralization and reference de-duplication only.

## Run Evidence

| Metric | Value |
|---|---:|
| Bar rows | 10,785,537 |
| Assets | 5,707 |
| Lead factor rows | 10,011,540 |
| Industry-neutral rows | 9,649,550 |
| Residual rows | 9,649,550 |
| Label rows | 10,751,318 |
| Reference factor rows | 74,585,970 |
| IC observations | 2,638 |
| Median raw cross-section | 3,666 |
| Median neutral/residual cross-section | 3,496 |
| Median industries per date | 110 |
| Highly redundant references | 2 |
| High style exposures | 0 |
| Portfolio preflight candidates | 0 |
| Promotion allowed | 0 |

## IC Results

| Layer | Mean IC | ICIR | t-stat | IC>0 | Yearly failures |
|---|---:|---:|---:|---:|---:|
| Raw | 0.0334 | 0.409 | 20.98 | 69.1% | 0 |
| Industry-neutral | 0.0295 | 0.468 | 24.02 | 72.1% | 0 |
| Industry + size/liquidity/vol residual | 0.0066 | 0.140 | 7.19 | 56.0% | 2 |

Interpretation: the raw Round155 signal was real enough to survive industry neutralization, but most of its strength disappears after size, liquidity, and volatility residualization. The residual layer is statistically positive but too weak for the project gate.

## Reference De-Duplication

| Reference | Class | Mean Abs Corr | Max Abs Corr | Decision |
|---|---|---:|---:|---|
| `rsrs_slope_inverse_raw_18_60` | highly redundant | 0.9845 | 0.9962 | blocker |
| `rsrs_slope_acceleration_quality_18_60` | highly redundant | 0.9367 | 0.9849 | blocker |
| `rsrs_residual_extreme_reversal_repair_18` | moderately redundant | 0.5476 | 0.8131 | caution |
| Other Donchian/efficiency/volume/kbar references | unique | 0.1510-0.2619 | 0.4858-0.6035 | no blocker |

The lead is essentially an inverse RSRS cluster expression, not a new independent technical edge.

## Style Exposure Check

| Exposure | Class | Mean Abs Corr | Max Abs Corr |
|---|---|---:|---:|
| `realized_vol_20` | low exposure | 0.2989 | 0.6024 |
| `amount_trend_20_60` | low exposure | 0.3092 | 0.5507 |
| `return_20` | low exposure | 0.1993 | 0.5778 |
| `log_amount` | low exposure | 0.1256 | 0.5555 |
| `log_adv20_amount` | low exposure | 0.1297 | 0.4491 |

No direct high size, liquidity, or volatility exposure was found. The failure came from residual alpha weakness and RSRS reference redundancy, not from a simple liquidity disguise.

## Residual Stability

Residual IC failed the yearly stability gate in 2018 and 2023:

| Year | Mean IC | IC>0 | Failure |
|---:|---:|---:|---|
| 2018 | 0.0010 | 49.8% | yes |
| 2023 | 0.0006 | 48.8% | yes |

This matters because the residual signal is already small; years with near-zero IC and sub-50% positive IC rate make it unsuitable for a costed portfolio grid.

## Decision

- Useful as evidence: yes. It shows public RSRS inverse/failure-reversal can produce raw and industry-neutral IC.
- Independent alpha: no.
- Portfolio grid: blocked.
- Promotion/manual/live: blocked.
- Next direction: `round157_rotate_after_public_technical_failure_reversal_neutral_dedup_failure`.

Round157 should rotate away from this RSRS cluster. If public technical methods continue, use a different economic mechanism rather than more RSRS parameter tuning.
