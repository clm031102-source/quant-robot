# CN Stock Public Alpha101 Reference Exposure Dedup - Round116

## Summary

Round116 audited the only Round115 research lead, `qlib_alpha158_return_std_position_blend_20` at 5-day horizon.

- Runtime artifact: `data/reports/public_alpha101_reference_exposure_dedup_round116_20260622`
- Lead rows: 10,130,080
- Reference factor rows: 60,727,542
- Exposure rows: 9,946,385
- IC observations: 2,661
- Mean IC: 0.04146
- ICIR: 0.323
- t-stat: 16.68
- IC positive rate: 63.40%
- Yearly failures: 0
- Monthly failures: 39
- Highly redundant references: 5
- High exposure diagnostics: 4
- Promotion allowed: 0
- Portfolio grid allowed: false
- Next direction: `round117_round114_116_three_round_review_before_next_action`

The signal is statistically real enough to study, but it is not independent enough to promote. The hard blockers are reference redundancy and exposure dependence.

## Reference Redundancy

| Reference | Obs | Mean Corr | Mean Abs Corr | Max Abs Corr | Class |
|---|---:|---:|---:|---:|---|
| `amount_stability_reversal_5_20` | 534 | 0.7384 | 0.7384 | 0.9288 | highly_redundant |
| `range_contraction_lowvol_reversal_20` | 534 | 0.6929 | 0.7070 | 0.9806 | highly_redundant |
| `pv_lowvol_reversal_blend_20` | 533 | 0.6616 | 0.6690 | 0.8642 | highly_redundant |
| `bollinger_reversal_lowvol_liquid_20` | 533 | 0.6622 | 0.6639 | 0.8841 | highly_redundant |
| `donchian_pullback_lowvol_liquid_20` | 534 | 0.3481 | 0.3568 | 0.9936 | highly_redundant |
| `rsi_reversal_lowvol_liquid_14_20` | 533 | 0.4938 | 0.4960 | 0.7923 | moderately_redundant |

Interpretation:

The lead is mostly a known low-volatility/reversal/liquidity blend. It is not a new independent Alpha101 edge. The Qlib-style blend may still be useful as a better representative of this cluster, but it cannot be promoted as a new factor without deduped incremental evidence.

## Exposure Diagnostics

| Exposure | Obs | Mean Corr | Mean Abs Corr | Max Abs Corr | Class |
|---|---:|---:|---:|---:|---|
| `log_adv20_amount` | 534 | 0.1250 | 0.1694 | 0.9929 | high_exposure |
| `market_corr_60` | 527 | 0.0209 | 0.1357 | 0.9059 | high_exposure |
| `beta_120` | 527 | -0.1187 | 0.2275 | 0.9049 | high_exposure |
| `downside_beta_120` | 524 | -0.1136 | 0.2030 | 0.8996 | high_exposure |
| `residual_vol_60` | 523 | -0.1707 | 0.2204 | 0.6328 | low_exposure |

Interpretation:

Average exposure is not extreme, but the maximum absolute correlations are too high on some dates. This means the signal can become a liquidity/beta/market-correlation proxy in particular regimes. That blocks direct portfolio conversion.

## Yearly Stability

The annual IC test is the bright spot. Every year from 2015 through 2025 had positive mean IC and positive IC rate above 50%.

Best years:

- 2024: mean IC 0.06348, IC+ 68.46%
- 2019: mean IC 0.05902, IC+ 71.31%
- 2016: mean IC 0.04749, IC+ 65.57%
- 2025: mean IC 0.04667, IC+ 66.53%

Weak but still positive years:

- 2023: mean IC 0.02274, IC+ 57.85%
- 2015: mean IC 0.02558, IC+ 57.74%

## Decision

Promotion remains blocked.

Blockers:

- `lead_highly_redundant_with_reference_factor`
- `lead_high_exposure_to_market_or_liquidity_proxy`

Because Round114, Round115, and Round116 are now complete, the next step must be the required three-round review:

`round117_round114_116_three_round_review_before_next_action`

The post-review recommendation is to hibernate this as a standalone public Alpha101/Qlib factor unless the next review chooses a very specific deduped bridge, such as an incremental residualized version of the Qlib blend against the low-vol/reversal/liquidity cluster.
