# CN Stock Low-Vol/Reversal/Liquidity Incremental Residual Prescreen - Round120

## Summary

Round120 tested the Round119 pre-registered incremental-residual candidates on the full CN stock long-cycle sample.

- Runtime artifact: `data/reports/lowvol_reversal_liquidity_incremental_residual_prescreen_round120_fixed_20260622`
- Analysis window: 2015-01-01 through 2025-12-31
- Final holdout: 2026 not included
- Candidates: 8
- Horizons: 5, 10, 20
- Factor rows: 79,947,068
- Label rows: 32,140,060
- Aligned rows: 238,172,035
- Tests: 24 factor x horizon tests
- FDR-significant tests: 22
- Raw statistical research leads: 1
- Incremental research leads after redundancy and exposure gates: 0
- Promotion allowed: 0
- Next direction: `round121_round118_120_three_round_review_before_next_action`

The important result is not that the line found a tradable factor. It did not. The important result is that the process caught a statistically attractive factor that was still too close to its parent/reference factor to count as new alpha.

## Fixed Audit Note

The first Round120 run produced valid IC and quantile statistics, but the reference-correlation audit sampled candidate dates and reference dates independently. Because the candidate and reference matrices had different start dates, the sampled dates could be phase-shifted, creating false zero-overlap rows.

The code was fixed to sample candidate dates first and filter reference factors to the same dates. A regression test now covers this date-sampling issue.

Use the fixed artifact only:

`data/reports/lowvol_reversal_liquidity_incremental_residual_prescreen_round120_fixed_20260622`

## Brightest Raw Result

| Factor | Horizon | IC | ICIR | t-stat | IC positive | Q5-Q1 | Monotonicity | Top turnover | Raw lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `range_contraction_incremental_residual_20` | 20 | 0.0548 | 0.530 | 27.10 | 68.6% | 0.06349 | 0.900 | 21.7% | yes |

This is a strong Alphalens-style statistical lead before the redundancy gate.

## Why It Is Not Promotable

The same raw lead is blocked by the fixed reference audit:

| Candidate | Reference | Obs | Mean abs corr | Max abs corr | Class |
|---|---|---:|---:|---:|---|
| `range_contraction_incremental_residual_20` | `range_contraction_lowvol_reversal_20` | 264 | 0.4639 | 0.9001 | highly redundant |

The factor still spikes to very high cross-sectional correlation with the original range-contraction parent. It is therefore not clean incremental alpha, even though its IC and quantile spread look good.

## Other Major Rejections

| Factor | Horizon | IC | ICIR | t-stat | Main reason |
|---|---:|---:|---:|---:|---|
| `qlib_blend_residual_vs_lowvol_cluster_5` | 20 | -0.0601 | -0.690 | -35.44 | Wrong signed direction and high liquidity exposure |
| `qlib_blend_residual_vs_lowvol_cluster_5` | 10 | -0.0529 | -0.605 | -31.17 | Wrong signed direction |
| `range_contraction_incremental_residual_20` | 10 | 0.0462 | 0.435 | 22.26 | Weak monotonicity |
| `qlib_blend_residual_vs_lowvol_cluster_5` | 5 | -0.0449 | -0.507 | -26.11 | Wrong signed direction |
| `range_contraction_incremental_residual_20` | 5 | 0.0406 | 0.383 | 19.63 | Weak monotonicity |
| `qlib_blend_cluster_exposure_neutral_residual_5` | 20 | -0.0248 | -0.341 | -17.36 | Wrong signed direction |
| `qlib_blend_cluster_exposure_neutral_residual_5` | 10 | -0.0244 | -0.334 | -17.04 | Wrong signed direction |

Several negative-IC candidates may be useful as inverse hypotheses later, but they require new preregistration. They should not be flipped directly from this screen.

## Redundancy And Exposure Blockers

Highly redundant rows:

- `bollinger_reversal_incremental_residual_20` vs `bollinger_reversal_lowvol_liquid_20`: max abs corr 0.9455.
- `bollinger_reversal_incremental_residual_20` vs `donchian_pullback_lowvol_liquid_20`: max abs corr 0.8571.
- `donchian_pullback_incremental_residual_20` vs `donchian_pullback_lowvol_liquid_20`: max abs corr 0.8949.
- `qlib_blend_residual_vs_lowvol_cluster_5` vs `donchian_pullback_lowvol_liquid_20`: max abs corr 0.8734.
- `range_contraction_incremental_residual_20` vs `range_contraction_lowvol_reversal_20`: max abs corr 0.9001.
- `rsi_reversal_incremental_residual_14_20` vs `rsi_reversal_lowvol_liquid_14_20`: max abs corr 0.8751.

Exposure blockers:

- `qlib_blend_residual_vs_lowvol_cluster_5` vs `log_adv20_amount`: high exposure, max abs corr 0.9085, mean abs corr 0.3288.
- `donchian_pullback_incremental_residual_20` vs `log_adv20_amount`: moderate exposure, max abs corr 0.8486.

## Decision

Do not continue this exact incremental-residual family as the next mining line. It produced useful diagnostics, but after fixing the reference audit it produced:

- 0 promotable factors.
- 0 true incremental research leads.
- 1 raw IC lead that is still too redundant with its source/reference factor.

Next required action:

`round121_round118_120_three_round_review_before_next_action`

The Round121 review should combine:

- Round118: soft-capacity low-turnover early stop after zero positive relative OOS rows.
- Round119: 8 incremental-residual candidates preregistered, no promotion.
- Round120: 8 candidates prescreened, 1 raw lead, 0 true incremental leads after fixed redundancy/exposure gates.

## Process Lesson

The direction was better than blind moneyflow continuation, but the engineering process still needs one improvement: full-sample prescreens must persist reusable factor matrices or support chunked correlation diagnostics. The fixed run was correct, but slow and memory heavy. Future rounds should avoid recomputing the same 2015-2025 labels/reference matrices for each family.
