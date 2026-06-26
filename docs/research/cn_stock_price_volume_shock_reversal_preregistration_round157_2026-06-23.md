# CN Stock Price-Volume Shock Reversal Preregistration Round157

## Summary

- Stage: `price_volume_shock_reversal_preregistration`
- Market/scope: CN A-share stocks only
- Generated candidates: 8
- Candidate families: 7
- RSRS candidates: 0
- Portfolio backtest allowed candidates: 0
- Promotion allowed candidates: 0
- Blockers: none
- Source audit: `docs/research/cn_stock_round154_156_three_round_review_2026-06-23.md`
- Negative evidence audit: `docs/research/cn_stock_public_technical_failure_reversal_neutral_dedup_round156_2026-06-23.md`
- Next required gate: `round158_price_volume_shock_reversal_neutral_prescreen`

## Why This Round Exists

Round156 showed that the public technical failure-reversal line had real raw and industry-neutral IC, but the lead was not independent after residualization and reference deduplication. The strongest lead was highly redundant with RSRS public references and produced zero portfolio preflight candidates. Continuing to tune RSRS windows would be parameter grinding, not new research.

Round157 therefore rotates to a different public, economically interpretable family: price-volume shock reversal and liquidity-stress normalization. The new family is still technical, but the thesis is no longer RSRS channel slope. It tests whether forced selling, volume climax, range expansion, gap/range failure, VWAP-proxy reclaim, or post-shock volatility compression can predict short-horizon cross-sectional recovery after strict neutralization.

## Candidate Set

| Factor | Family | Windows | Thesis |
|---|---|---:|---|
| `amihud_shock_reversal_liquid_20_60` | `liquidity_stress_reversal` | 5/20/60 | Temporary liquidity stress plus price damage may mean supply exhaustion if liquidity remains tradable. |
| `volume_climax_reversal_close_location_20` | `volume_climax_exhaustion` | 5/20 | Heavy turnover with weak close location may indicate panic selling or forced exit. |
| `range_expansion_exhaustion_reversal_20` | `range_expansion_exhaustion` | 5/20 | Range expansion after price damage may be capitulation when capacity filters are respected. |
| `downside_volume_absorption_reversal_10_60` | `downside_volume_absorption` | 10/20/60 | Down-day volume concentration may indicate supply absorption after volatility control. |
| `gap_range_failure_reversal_5_20` | `gap_range_failure_reversal` | 1/5/20 | Uses gap plus range failure, not pure overnight gap continuation. |
| `vwap_proxy_reclaim_reversal_20` | `vwap_proxy_reclaim` | 5/20 | Daily amount/volume VWAP proxy reclaim may indicate pressure relief; unit consistency must be audited. |
| `low_liquidity_stress_normalization_20_60` | `liquidity_stress_reversal` | 20/60 | Separates temporary stress from persistent illiquidity to avoid microcap tail bets. |
| `volatility_compression_after_shock_reversal_20_60` | `post_shock_volatility_compression` | 5/10/20/60 | Shock followed by volatility compression may indicate stabilization; must dedup against old low-vol reversal clusters. |

## Mandatory Round158 Gate

Round158 must run long-cycle neutral prescreening before any portfolio conversion:

- Full 2015-2025 sample, not a short 2023-2024 discovery slice.
- Execution lag of at least one trading day.
- No final-holdout tuning.
- Industry neutral IC.
- Size, liquidity, volatility, and recent-return residual IC.
- Reference correlation dedup against old low-vol reversal, price-volume reversal, gap, and RSRS clusters.
- Multiple-testing accounting across all 8 preregistered candidates and all tested horizons.
- Event contamination and limit-up/down tradeability audit before any promotion claim.

## Decision

This round creates no profitability claim. It only fixes the research direction after the RSRS redundancy failure and creates a repeatable, auditable next step. Direct TopN grids, walk-forward champion selection, or promotion from this preregistration are blocked.
