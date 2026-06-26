# CN Stock Alpha101 Rank PV Reversal Residual Prescreen - Round130

## Scope

- Machine role: office_desktop factor validation.
- Market and asset: CN stock cross-sectional alpha.
- Source audit: `docs/research/cn_stock_alpha101_rank_pv_reversal_reference_dedup_round129_2026-06-22.md`.
- Output root: `data/reports/alpha101_rank_pv_reversal_residual_prescreen_round130_20260622`.
- Stage: residual IC audit only; no portfolio grid and no promotion.

## Why This Round Exists

Round129 showed that `alpha101_rank_pv_reversal_liquid_20` had real full-sample IC, but it was highly redundant with three existing price-volume references:

- `pv_corr_reversal_capacity_safe_20`
- `pv_lowvol_reversal_blend_20`
- `raw_neg_pv_corr_20`

The correct question for Round130 was therefore not "can the raw factor earn money?", but "does anything useful remain after removing the known price-volume reversal cluster?"

## Run Evidence

- Data window: 2015-01-05 to 2025-12-31.
- Bars: 10,785,537 rows, 5,707 assets.
- Signal rows before residualization: 10,107,084.
- Residual rows: 10,107,084.
- Label rows: 10,665,909.
- IC observations: 2,641.
- Final holdout: not included.

## Residualization Result

The three-reference cluster explains nearly all of the original signal:

| Metric | Value |
|---|---:|
| Diagnostic dates | 2,662 |
| Median cross-section | 3,685 |
| Mean R-squared | 0.9840 |
| Median R-squared | 0.9842 |
| Mean residual std | 0.0745 |
| Median residual std | 0.0814 |
| Median lead std | 0.6426 |

This means the original lead was mostly the same price-volume reversal/liquidity exposure in a different wrapper.

## Residual IC

Residual IC does not survive. It reverses direction and fails significance/stability gates:

| IC Obs | Mean IC | ICIR | t-stat | IC>0 | Median CS |
|---:|---:|---:|---:|---:|---:|
| 2,641 | -0.0323 | -0.199 | -10.21 | 39.0% | 3,670 |

## Yearly Residual IC

| Year | Obs | Mean IC | IC+ | Failure |
|---:|---:|---:|---:|---|
| 2015 | 234 | 0.0271 | 57.3% | False |
| 2016 | 244 | -0.0247 | 48.8% | True |
| 2017 | 244 | -0.1053 | 28.3% | True |
| 2018 | 243 | -0.0225 | 37.9% | True |
| 2019 | 244 | -0.0517 | 27.5% | True |
| 2020 | 243 | -0.0856 | 22.6% | True |
| 2021 | 243 | -0.0390 | 35.8% | True |
| 2022 | 242 | -0.0207 | 43.0% | True |
| 2023 | 242 | 0.0240 | 47.9% | True |
| 2024 | 241 | -0.0350 | 44.0% | True |
| 2025 | 221 | -0.0179 | 36.7% | True |

## Gate Decision

- Promotable factors: 0.
- Portfolio-grid permission: 0.
- Residual walk-forward preregistration permission: 0.
- Gate blockers:
  - `residual_ic_below_threshold`
  - `residual_icir_below_threshold`
  - `residual_t_stat_below_threshold`
  - `residual_positive_ic_rate_below_threshold`
  - `yearly_ic_instability`

User drawdown tolerance can relax a MaxDD screen, but it cannot waive redundancy, negative residual IC, look-ahead, overfit, cost, capacity, or walk-forward gates.

## Conclusion

`alpha101_rank_pv_reversal_liquid_20` should not be promoted and should not be expanded into a portfolio grid. After removing the known PV reversal cluster, the remaining signal is significantly negative and unstable across years. Continuing this line would be a low-value parameter search around a rejected exposure.

## Next Direction

Set the repeatable startup direction to:

`round131_rotate_to_non_price_volume_public_reference_or_daily_basic_family`

Allowed next work:

- hibernate the Alpha101/PV reversal residual line;
- rotate to a non-price-volume public-reference family or daily-basic/financial-quality family;
- pre-register the new family before running full-sample screens;
- keep the long-cycle, multiple-testing, capacity, cost, and regime gates active.
