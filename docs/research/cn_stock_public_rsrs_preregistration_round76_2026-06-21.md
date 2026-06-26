# CN Stock Public RSRS Pre-Registration Round 76 - 2026-06-21

## Purpose

Round75 hibernated the public risk-filter bridge family as a promotion path. Round76 rotates to a different public-method family instead of spending more budget on the failed line.

The new family is RSRS, a public A-share technical method based on the rolling regression slope of high price against low price. The economic idea is that a strong high-low regression slope and slope z-score may describe support/resistance strength and breakout pressure. Because trend-style public methods have often failed in this CN stock universe, the batch pre-registers both directional and reversal variants.

## Registered Factors

- `rsrs_slope_18`: rolling 18-day high-on-low regression slope.
- `rsrs_zscore_18_60`: 60-day z-score of the 18-day RSRS slope.
- `rsrs_right_skew_18_60`: RSRS z-score weighted by rolling regression R2.
- `rsrs_reversal_18_60`: negative `rsrs_right_skew_18_60`.

## Guardrails

- No future data: rolling windows use only current and past rows.
- No 2026 tuning: configured sample is 2015-01-05 through 2025-12-31.
- No broad parameter search: one standard RSRS shape, one reversal counterpart, top50/top100, rebalance 10 only.
- Promotion blocked unless cost, capacity, drawdown, overlap-aware statistics, fold stability, and long-cycle evidence all pass.

## Config

- `configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`

## Next Step

Run the long-cycle costed RSRS experiment grid. If all long-only variants fail, do not expand RSRS windows; first run IC-to-portfolio and quantile-shape diagnostics to see whether the useful side is top selection, bottom avoidance, or no signal.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
