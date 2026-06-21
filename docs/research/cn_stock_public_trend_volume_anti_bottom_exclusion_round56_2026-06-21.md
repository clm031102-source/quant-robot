# CN Stock Public Trend-Volume Anti Bottom-Exclusion Round 56 - 2026-06-21

## Purpose

Rounds 7-9 already showed that raw public trend-volume continuation was wrong-way for CN stocks and that the inverse side had positive IC but weak direct TopN performance.

Round56 therefore did not rerun Supertrend/OBV as a buy signal. It used the existing `public_trend_volume` source as a risk-filter translation layer:

- `anti_supertrend_volume_confirmed_10_3_20`
- `anti_smart_money_trend_20`
- `anti_obv_breakout_low_tail_20`

This follows the public-project evaluation pattern: check IC/quantile behavior first, then require costed portfolio evidence before any promotion. Qlib benchmark docs emphasize both alpha/future-return correlation and portfolio evaluation; Alphalens centers factor diagnostics around returns, IC, and turnover; vectorbt-style signal testing keeps the portfolio simulation explicit.

References:

- https://github.com/microsoft/qlib
- https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md
- https://quantopian.github.io/alphalens/
- https://vectorbt.dev/api/portfolio/base/

## Overlay Audit

Config:

- `configs/experiment_grid_cn_stock_public_trend_volume_anti_fast_20260621.json`
- source: `authority-processed-bars`
- authority bars: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- period: 2015-01-05 through 2025-12-31
- factor source: `public_trend_volume`
- bottom exclusion: bottom 20%
- horizon: 20
- execution lag: 1

### Rebalance 5

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `anti_supertrend_volume_confirmed_10_3_20` | bottom-exclusion candidate | -0.0034 | -0.0007 | -0.0137 | 0.0025 | 9.31 | 67.24% | -88.62% | -99.99% |
| `anti_smart_money_trend_20` | bottom-exclusion candidate | -0.0022 | 0.0003 | -0.0130 | 0.0026 | 8.36 | 66.73% | -79.67% | -99.99% |
| `anti_obv_breakout_low_tail_20` | bottom-exclusion candidate | 0.0036 | 0.0056 | -0.0046 | 0.0020 | 8.07 | 64.64% | 235.69% | -98.73% |

### Rebalance 10

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `anti_supertrend_volume_confirmed_10_3_20` | bottom-exclusion candidate | -0.0029 | -0.0002 | -0.0142 | 0.0027 | 7.00 | 68.82% | -62.65% | -99.33% |
| `anti_obv_breakout_low_tail_20` | bottom-exclusion candidate | 0.0040 | 0.0061 | -0.0047 | 0.0022 | 6.14 | 65.40% | 98.43% | -89.54% |
| `anti_smart_money_trend_20` | bottom-exclusion candidate | -0.0019 | 0.0010 | -0.0142 | 0.0029 | 6.11 | 67.68% | -47.59% | -99.35% |

## Costed Risk-Filter Portfolio

Shared settings:

- bottom exclusion: 20%
- holding period: 20
- cost: 10 bps
- market impact: 20 bps
- max participation: 1% ADV
- liquidity floor: entry amount >= 10,000,000
- portfolio value: 1,000,000

### Rebalance 5

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `anti_obv_breakout_low_tail_20` | research lead | 46.57% | 12.74% | 33.83% | 0.1834 | 0.1014 | -59.20% | 46.00% | 10/11 | 0 |
| `anti_smart_money_trend_20` | weak/unproven | -22.96% | -44.69% | 21.73% | -0.0642 | -0.0344 | -77.55% | 42.92% | 10/11 | 0 |
| `anti_supertrend_volume_confirmed_10_3_20` | weak/unproven | -36.26% | -55.32% | 19.06% | -0.1417 | -0.0739 | -81.21% | 43.73% | 10/11 | 0 |

### Rebalance 10

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `anti_obv_breakout_low_tail_20` | research lead | 41.13% | 6.92% | 34.21% | 0.1178 | 0.0907 | -60.06% | 46.62% | 10/11 | 0 |
| `anti_smart_money_trend_20` | weak/unproven | -20.77% | -45.52% | 24.75% | -0.0057 | -0.0042 | -76.54% | 45.06% | 10/11 | 0 |
| `anti_supertrend_volume_confirmed_10_3_20` | weak/unproven | -38.47% | -56.40% | 17.93% | -0.0679 | -0.0483 | -81.61% | 45.50% | 10/11 | 0 |

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Risk-filter research lead:

- `anti_obv_breakout_low_tail_20`

Hibernate:

- `anti_supertrend_volume_confirmed_10_3_20` as a standalone risk filter,
- `anti_smart_money_trend_20` as a standalone risk filter,
- any raw trend-continuation TopN expansion.

## Interpretation

The public trend-volume family is useful only as a warning system.

The bottom tail of the inverse OBV breakout factor repeatedly identifies a severe bad-stock bucket. Excluding that bucket improves relative return in 10 of 11 yearly folds and clears capacity limits after the 10m liquidity floor.

It still does not pass promotion because:

- overlap-adjusted Sharpe stays near 0.09-0.10,
- max drawdown remains around -59% to -60%,
- absolute Sharpe is below 0.20,
- the filter works more as drawdown avoidance and relative improvement than as a complete return engine.

## Next Direction

Round57 should stop single-filter testing and build a composite risk-filter bridge:

- combine `anti_obv_breakout_low_tail_20` with Round55 `smart_money_reversal_value_20`,
- require agreement across at least two independent risk filters before exclusion,
- compare union, intersection, and weighted-score exclusion policies,
- keep the same cost, capacity, overlap, and yearly-fold gates,
- only promote if the composite improves drawdown and overlap Sharpe, not just relative return.

This is the most efficient next step because two independent families now point to the same shape of evidence: bottom-tail exclusion works better than direct long-only buying, but single filters are not strong enough alone.
