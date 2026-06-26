# CN Stock Alpha101 Rank PV Reversal Reference Dedup - Round129

## Scope

- Machine role: office_desktop factor validation.
- Market and asset: CN stock cross-sectional alpha.
- Source prescreen: `docs/research/cn_stock_public_reference_multi_family_prescreen_round128_2026-06-22.md`.
- Source review: `docs/research/cn_stock_round126_128_three_round_review_2026-06-22.md`.
- Output root: `data/reports/alpha101_rank_pv_reversal_reference_dedup_round129_20260622`.
- Stage: lead de-duplication and stability audit only.

## Run Evidence

- Data window: 2015-01-05 to 2025-12-31.
- Bars: 10,785,537 rows, 5,707 assets.
- Lead factor rows: 10,356,275.
- Reference factor rows: 18,670,665.
- Label rows: 10,665,909.
- Round128 evidence: 20 candidates, 60 factor-horizon tests, 3 research-lead rows.
- Unique Round128 lead factors: 1 (`alpha101_rank_pv_reversal_liquid_20`).
- Final holdout: not included.

## Lead IC

`alpha101_rank_pv_reversal_liquid_20` remains a real statistical signal:

| Horizon | IC Obs | Mean IC | ICIR | t-stat | IC>0 | Median CS |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 2,641 | 0.0457 | 0.473 | 24.29 | 68.1% | 3,751 |

This is not weak discovery evidence. The problem is not lack of IC; the problem is lack of independent alpha identity after reference de-duplication.

## Reference Correlation

| Reference | Obs | Mean Abs Corr | Max Abs Corr | Class |
|---|---:|---:|---:|---|
| `pv_lowvol_reversal_blend_20` | 533 | 0.9046 | 0.9789 | highly_redundant |
| `pv_corr_reversal_capacity_safe_20` | 533 | 0.9043 | 0.9934 | highly_redundant |
| `raw_neg_pv_corr_20` | 533 | 0.8871 | 0.9779 | highly_redundant |
| `bollinger_reversal_lowvol_liquid_20` | 533 | 0.5287 | 0.7922 | moderately_redundant |
| `raw_reversal_5` | 533 | 0.4813 | 0.8133 | moderately_redundant |
| `alpha101_decay_reversal_amount_stability_10` | 532 | 0.4021 | 0.6449 | unique |
| `amount_stability_reversal_5_20` | 533 | 0.3707 | 0.7433 | moderately_redundant |
| `raw_neg_realized_vol_20` | 533 | 0.1785 | 0.7073 | moderately_redundant |
| `raw_log_adv20` | 533 | 0.1135 | 0.4107 | unique |

## Stability

Yearly IC is positive in most years, but 2023 fails:

| Year | Mean IC | IC>0 | Failure |
|---:|---:|---:|---|
| 2015 | 0.0171 | 52.6% | False |
| 2016 | 0.0412 | 67.6% | False |
| 2017 | 0.0782 | 76.2% | False |
| 2018 | 0.0676 | 77.8% | False |
| 2019 | 0.0534 | 75.0% | False |
| 2020 | 0.0395 | 72.0% | False |
| 2021 | 0.0253 | 61.7% | False |
| 2022 | 0.0756 | 76.4% | False |
| 2023 | -0.0113 | 45.0% | True |
| 2024 | 0.0729 | 74.7% | False |
| 2025 | 0.0423 | 69.7% | False |

## Decision

- Promotable factors: 0.
- Portfolio-grid permission: 0.
- Research lead retained as signal evidence: yes.
- Independent new alpha candidate: no.
- Gate blockers:
  - `round128_multi_horizon_leads_not_independent`
  - `lead_highly_redundant_with_reference_factor`
  - `yearly_ic_instability`

The user can tolerate around 30% drawdown, but drawdown tolerance does not waive redundancy, cost, capacity, or walk-forward gates. This lead should not be pushed into a direct long-only or TopN portfolio grid.

## Next Direction

Set the repeatable startup direction to:

`round130_alpha101_rank_pv_reversal_hibernate_or_orthogonalize_after_dedup`

Allowed next work:

- hibernate direct `alpha101_rank_pv_reversal_liquid_20` portfolio expansion;
- only continue this line through a pre-registered orthogonal/residual test against `pv_corr_reversal_capacity_safe_20`, `pv_lowvol_reversal_blend_20`, and `raw_neg_pv_corr_20`;
- otherwise rotate to a different public-reference family or a non-price-volume daily-basic/financial line.
