# CN Stock Round114-116 Three-Round Review

## Scope

This review covers the three post-Round113 rounds:

- Round114: public Alpha101/Qlib-style capacity-safe preregistration.
- Round115: public Alpha101 IC/quantile/turnover/capacity prescreen.
- Round116: reference redundancy and exposure dedup for the only Round115 lead.

## What Worked

The workflow improved materially:

- No random formula sweep.
- No short-window-only mining.
- No portfolio grid before IC/quantile/turnover/capacity gates.
- No promotion from preregistration.
- No direct promotion from a high-IC line before redundancy and exposure audit.

The public-method rotation also produced one real research lead:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `qlib_alpha158_return_std_position_blend_20` | 5 | 0.0415 | 0.323 | 16.68 | 63.4% | 0.01794 | 0.900 | 34.9% |

The lead was robust by yearly IC:

- 2015-2025 all years had positive mean IC.
- 2015 did not fail: mean IC 0.02558, IC+ 57.74%.
- 2024 was strong: mean IC 0.06348, IC+ 68.46%.
- 2025 remained positive: mean IC 0.04667, IC+ 66.53%.

## What Failed

The lead failed independent-alpha promotion because Round116 found strong redundancy:

| Reference | Mean Abs Corr | Max Abs Corr | Class |
|---|---:|---:|---|
| `amount_stability_reversal_5_20` | 0.7384 | 0.9288 | highly_redundant |
| `range_contraction_lowvol_reversal_20` | 0.7070 | 0.9806 | highly_redundant |
| `pv_lowvol_reversal_blend_20` | 0.6690 | 0.8642 | highly_redundant |
| `bollinger_reversal_lowvol_liquid_20` | 0.6639 | 0.8841 | highly_redundant |
| `donchian_pullback_lowvol_liquid_20` | 0.3568 | 0.9936 | highly_redundant |

It also had high episodic exposure:

| Exposure | Mean Abs Corr | Max Abs Corr | Class |
|---|---:|---:|---|
| `log_adv20_amount` | 0.1694 | 0.9929 | high_exposure |
| `market_corr_60` | 0.1357 | 0.9059 | high_exposure |
| `beta_120` | 0.2275 | 0.9049 | high_exposure |
| `downside_beta_120` | 0.2030 | 0.8996 | high_exposure |

So the signal is not useless, but it is not an independent factor. It is mostly a known low-volatility/reversal/liquidity cluster representative.

## Reject Reason Histogram

- 9/10 Round114 candidates did not become strict research leads.
- 27/30 tests were FDR-significant, but only 1 passed the stricter lead gate.
- 5 reference factors were highly redundant with the lead.
- 4 exposure diagnostics were high-exposure.
- 39 monthly IC buckets failed, even though all years stayed positive.
- 0 candidates are promotable.

## Decision

Hibernate direct public Alpha101/Qlib standalone promotion.

Do not do:

- More Alpha101 formula expansion before extracting incremental value.
- Direct portfolio grid for `qlib_alpha158_return_std_position_blend_20`.
- Inverting the negative-IC Alpha101 formulas without new preregistration.
- Treating high FDR significance as portfolio evidence.

## Next Direction

`round118_lowvol_reversal_liquidity_cluster_incremental_residual_preregistration`

Rationale:

The useful information is not "Alpha101 works." The useful information is that a stable low-vol/reversal/liquidity cluster exists, but it is redundant. Round118 should preregister a small set of incremental residual candidates that explicitly remove the known cluster and exposure components:

- residualize the Qlib blend against `amount_stability_reversal_5_20`, `range_contraction_lowvol_reversal_20`, `pv_lowvol_reversal_blend_20`, and `bollinger_reversal_lowvol_liquid_20`;
- neutralize or diagnose `log_adv20_amount`, `beta_120`, `downside_beta_120`, and `market_corr_60`;
- require incremental IC/quantile evidence over the existing cluster;
- keep portfolio grids blocked until incremental evidence survives.

## Bottom Line

This three-round block found one statistically useful lead and then correctly stopped it from becoming a fake promotable factor. That is a good outcome: the project avoided another expensive direct-portfolio detour and now has a more precise next hypothesis.
