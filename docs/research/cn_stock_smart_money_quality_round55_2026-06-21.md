# CN Stock Smart-Money Quality Round 55 - 2026-06-21

## Purpose

Round54 concluded that daily-basic residual composites were not worth another direct rerun. Round55 implemented a more explicit public-anomaly-inspired family:

- smart-money proxy from close location and amount,
- value and shareholder-yield context from Tushare daily-basic fields,
- downside-volatility and high-low range risk control,
- liquidity and crowding gates before ranking.

The family was tested on the long-cycle CN stock authority data, not on the legacy 2023-2024 short window.

## Experiment Grid

Config:

- `configs/experiment_grid_cn_stock_daily_basic_smart_money_quality_fast_20260621.json`
- market: CN stock
- period: 2015-01-05 through 2025-12-31
- factor source: `daily_basic_smart_money_quality`
- factors: `smart_money_quality_lowvol_20`, `smart_money_efficiency_lowvol_20`, `smart_money_reversal_value_20`
- horizon: 20
- execution lag: 1
- rebalance: 5 and 10
- top N: 50 and 100
- cost: 10 bps plus 20 bps market impact
- max participation: 1% ADV
- regime lookback: 120
- precomputed factor rows: 25,249,353

Grid result:

- cases: 12
- completed: 12
- failed: 0
- accepted direct long-only factors: 0

## Direct Long-Only Result

| Case | Total | Annual | Sharpe | Win | Max DD | Rank IC | Rank IC t | Relative | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `smart_money_reversal_value_20`, top100, reb5 | 31.43% | 2.22% | 0.3196 | 49.20% | -31.42% | 0.0830 | 8.73 | -2342.32% | rejected |
| `smart_money_quality_lowvol_20`, top50, reb5 | 24.76% | 2.29% | 0.3053 | 51.93% | -31.48% | 0.0747 | 7.57 | -2348.98% | rejected |
| `smart_money_reversal_value_20`, top50, reb5 | 25.30% | 2.25% | 0.2988 | 51.96% | -31.09% | 0.0830 | 8.73 | -2348.44% | rejected |
| `smart_money_efficiency_lowvol_20`, best case | -36.45% | -2.60% | -0.2210 | 45.27% | -51.38% | 0.0221 | 1.79 | -2410.20% | rejected |

Interpretation:

- `smart_money_reversal_value_20` and `smart_money_quality_lowvol_20` have real cross-sectional ranking signal.
- The signal does not convert into direct long-only profit after costs and the benchmark comparison.
- `smart_money_efficiency_lowvol_20` is not useful in this implementation.

## Bottom-Exclusion Overlay Audit

The direct buy signal failed, so the family was tested as a bottom-tail exclusion overlay.

### Rebalance 5

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `smart_money_reversal_value_20` | bottom-exclusion candidate | 0.0046 | 0.0060 | -0.0010 | 0.0014 | 4.12 | 58.98% | 252.35% | -96.89% |
| `smart_money_quality_lowvol_20` | bottom-exclusion candidate | 0.0046 | 0.0054 | 0.0017 | 0.0007 | 2.13 | 56.52% | 149.67% | -87.42% |
| `smart_money_efficiency_lowvol_20` | weak/unproven | 0.0046 | 0.0044 | 0.0056 | -0.0002 | -0.86 | 51.61% | 44.22% | 27.39% |

### Rebalance 10

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `smart_money_reversal_value_20` | bottom-exclusion candidate | 0.0054 | 0.0069 | -0.0006 | 0.0015 | 3.19 | 57.95% | 118.66% | -81.15% |
| `smart_money_quality_lowvol_20` | weak/unproven | 0.0054 | 0.0062 | 0.0023 | 0.0008 | 1.68 | 54.92% | 82.62% | -60.73% |
| `smart_money_efficiency_lowvol_20` | weak/unproven | 0.0054 | 0.0051 | 0.0064 | -0.0003 | -0.63 | 49.24% | 37.24% | 29.64% |

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
| `smart_money_reversal_value_20` | research lead | 53.66% | 26.70% | 26.97% | 0.1782 | 0.0983 | -61.27% | 47.38% | 9/11 | 0 |
| `smart_money_quality_lowvol_20` | research lead | 40.60% | 26.70% | 13.90% | 0.1486 | 0.0819 | -62.91% | 47.56% | 7/11 | 0 |
| `smart_money_efficiency_lowvol_20` | weak/unproven | 23.62% | 26.70% | -3.08% | 0.1059 | 0.0580 | -67.21% | 46.61% | 6/11 | 0 |

### Rebalance 10

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `smart_money_reversal_value_20` | research lead | 52.61% | 23.82% | 28.79% | 0.1168 | 0.0874 | -61.04% | 49.01% | 9/11 | 0 |
| `smart_money_quality_lowvol_20` | research lead | 39.22% | 23.82% | 15.40% | 0.1000 | 0.0746 | -63.77% | 49.57% | 7/11 | 0 |
| `smart_money_efficiency_lowvol_20` | weak/unproven | 21.53% | 23.82% | -2.29% | 0.0759 | 0.0564 | -68.02% | 49.39% | 6/11 | 0 |

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Risk-filter research leads:

- `smart_money_reversal_value_20`: useful as a bottom-tail diagnostic and possible component in a broader portfolio construction layer, not a standalone alpha.
- `smart_money_quality_lowvol_20`: weaker secondary exclusion component only.

Retire or hibernate:

- direct TopN long-only use of all three factors,
- `smart_money_efficiency_lowvol_20`,
- expanding this family by more parameter sweeps before a portfolio-construction bridge exists.

## Why This Was Still Useful

This round identified the IC-to-portfolio gap:

- The top tail is not attractive enough to buy directly.
- The bottom tail is consistently bad for `smart_money_reversal_value_20`.
- Costed broad-basket exclusion improves relative return, but not enough to overcome low Sharpe and deep drawdown.

So the family is not useless, but it is not a profit engine by itself.

## Next Direction

Stop extending the smart-money-quality family as a standalone alpha family.

Round56 should move to a public-indicator translation layer with the portfolio gate first:

- Supertrend or ATR trend state as a risk-regime and bottom-tail filter.
- Relative strength plus low volatility as a simple public anomaly baseline.
- Value/quality only as a tie-breaker or exclusion stabilizer, not as a direct long-only signal.
- Industry/size neutrality diagnostics before more TopN expansion.
- Costed bottom-exclusion and ETF-transferability checks before promotion claims.

The goal is to reduce search waste: test public, explainable anomalies through the same long-cycle, costed, overlap-aware gate before spending budget on more variants.
