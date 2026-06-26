# CN Stock Public Trend-Volume Round 7

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional alpha
- Data: repaired authority CN bars, 2015-01-05 to 2025-12-31
- Config: `configs/experiment_grid_cn_stock_public_trend_volume_fast_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_public_trend_volume_fast_20260621_repaired`

## Candidate Family

Round 7 rotated to public-method price-volume and trend-confirmation ideas:

- `supertrend_volume_confirmed_10_3_20`
- `smart_money_trend_20`
- `obv_breakout_low_tail_20`

These are inspired by common public technical workflows: ATR/SuperTrend-like trend state, smart-money-style directional amount pressure, OBV accumulation, Donchian breakout position, liquidity filter, and low-tail filter. They use only current and past bar fields.

## Long-Cycle Fast Grid

- Cases: 3
- Completed: 3
- Failed/no-trade: 0
- Factor matrix rows: 32,278,485
- IC observations: 526
- TopN/cost/rebalance: top100, 10 bps, rebalance every 5 bars
- Holding/execution: forward horizon 20, execution lag 1
- Capacity model: portfolio value 1,000,000, market impact 20 bps, max participation 1%

| factor | decision | total return | relative return | Sharpe | overlap-adj Sharpe | max DD | win rate | mean IC | mean RankIC | cap-limited trades | extreme flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `obv_breakout_low_tail_20` | rejected | -0.67 | -38.44 | -0.396 | -0.192 | -91.09% | 40.92% | -0.0341 | -0.0541 | 2 | true |
| `smart_money_trend_20` | rejected | -0.72 | -38.49 | -0.451 | -0.216 | -92.45% | 42.50% | -0.0491 | -0.0584 | 6 | true |
| `supertrend_volume_confirmed_10_3_20` | rejected | -0.78 | -38.55 | -0.566 | -0.278 | -93.47% | 41.42% | -0.0450 | -0.0568 | 2 | true |

## Audit Read

The long-only trend-chasing direction failed decisively.

Evidence:

- All three candidates have statistically significant negative IC.
- Long-short spreads are negative, and top quantile returns are below bottom quantile returns.
- Drawdowns are unacceptable, around -91% to -93%.
- Capacity-limited trades are present, although not widespread.
- Extreme trade flags remain, likely from residual single-name anomalies, but the factors are bad even with positive extreme trades included.

This is useful evidence: the public trend-volume construction appears to work in the opposite direction in this CN stock universe. High trend plus volume confirmation may represent crowding, overextension, or distribution risk rather than continuation.

## Decision

No Round 7 factor is promotable.

Direction for Round 8:

- Do not expand long-only trend-following parameters.
- Test explicit contrarian/inverted versions of the same three signals.
- Keep repaired authority bars and the same long-cycle full-sample gate.
- Treat the inversion as a pre-registered hypothesis from Round 7 negative IC, not as arbitrary sign flipping after a random search.
