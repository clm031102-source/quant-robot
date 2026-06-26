# CN Stock Daily-Basic Lead Dedup Round133

## Scope

- Machine role: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Stage: `daily_basic_non_price_public_carry_lead_dedup`
- Lead: `daily_basic_free_float_supply_quality_20`, horizon 20
- Input audit: `docs/research/cn_stock_daily_basic_non_price_public_carry_prescreen_round132_2026-06-22.md`
- Output pack: `data/reports/daily_basic_non_price_public_carry_lead_dedup_round133_20260622`
- Final holdout: not included

## Data Window

| Item | Value |
|---|---:|
| Bar rows | 10,785,537 |
| Bar assets | 5,707 |
| Bar date range | 2015-01-05 to 2025-12-31 |
| Daily-basic rows | 3,262,000 |
| Daily-basic assets | 5,567 |
| Daily-basic date range | 2023-07-03 to 2025-12-31 |
| Lead factor rows | 3,262,000 |
| Reference factor rows | 29,358,000 |
| Label rows | 10,665,909 |

## Result Summary

Round133 did not promote a factor, but it materially improved the evidence quality for the Round132 lead.

| Metric | Raw lead | Implementation-residual lead |
|---|---:|---:|
| IC observations | 586 | 586 |
| Mean IC | 0.039225 | 0.034488 |
| ICIR | 0.311307 | 0.525926 |
| t-stat | 7.535934 | 12.731320 |
| IC positive rate | 63.48% | 74.91% |
| Median cross-section | 5,349 | 3,722 |

Interpretation:

- The lead is not just another daily-basic candidate clone. No preregistered daily-basic reference factor reached the high redundancy gate.
- The lead is not a simple implementation exposure. Size, value, dividend, volume-ratio, and ADV exposure correlations stayed below hard thresholds.
- The strongest correlations are expected thesis exposures: `free_share_to_total_share` mean abs corr 0.8618 and `float_share_to_total_share` mean abs corr 0.6052.
- After neutralizing `log_circ_mv`, `log_total_mv`, `inv_pb`, `dv_ttm`, and `log_adv20_amount`, the residual signal still has positive mean IC and stronger ICIR.

## Blocker

Promotion and portfolio conversion remain blocked by residual yearly instability:

| Year | Residual IC obs | Residual mean IC | Residual IC+ | Failure |
|---:|---:|---:|---:|---|
| 2023 | 124 | -0.016507 | 43.55% | true |
| 2024 | 241 | 0.035552 | 81.33% | false |
| 2025 | 221 | 0.061939 | 85.52% | false |

Raw yearly IC did not fail:

| Year | Raw IC obs | Raw mean IC | Raw IC+ | Failure |
|---:|---:|---:|---:|---|
| 2023 | 124 | 0.007180 | 57.26% | false |
| 2024 | 241 | 0.038937 | 69.71% | false |
| 2025 | 221 | 0.057520 | 60.18% | false |

The useful lesson is narrow: the lead deserves a stability audit, not direct promotion and not immediate family abandonment.

## Decision

- Promotion allowed: `false`
- Portfolio conversion candidate: `false`
- Hard implementation exposure blocker: `false`
- Hard reference redundancy blocker: `false`
- Active blocker: `residual_yearly_ic_instability`
- Next direction: `round134_daily_basic_free_float_supply_quality_residual_stability_audit`

## Required Round134 Work

Round134 must determine whether the 2023 residual failure is caused by a known, controllable state or by a genuine regime break.

Required checks:

- Split 2023 residual IC by month, market regime, breadth, and volatility state.
- Compare raw vs residual signal around 2023-07, 2023-08, 2023-11, 2023-12, 2024-02, and 2025-04 weak months.
- Audit whether daily-basic coverage onset in 2023-07 creates transient alignment or coverage artifacts.
- Re-run residual IC with a stricter coverage/capacity clean mask before any portfolio grid.
- If instability remains unexplained, hibernate the share-structure daily-basic line and rotate family.

## Safety

This is research-to-review only. No broker connection, no account reads, no order placement, and no live trading.
