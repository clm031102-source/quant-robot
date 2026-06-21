# CN Stock Composite Risk-Filter Bridge Round 57 - 2026-06-21

## Purpose

Round55 found that `smart_money_reversal_value_20` had strong IC and a bad bottom bucket, but failed as a direct long-only factor.

Round56 found that `anti_obv_breakout_low_tail_20` was the cleanest public trend-volume risk filter, but also failed promotion as a standalone filter.

Round57 therefore tested a pre-registered bridge source:

- `risk_filter_bridge_equal_20`
- `risk_filter_bridge_agreement_20`
- `risk_filter_bridge_anti_obv_weighted_20`

The bridge combines two independent warning systems:

- public OBV breakout/tail risk, from `anti_obv_breakout_low_tail_20`;
- daily-basic smart-money reversal/value risk, from `smart_money_reversal_value_20`.

Low factor scores represent the excluded bottom bucket. This round is a risk-filter validation, not a direct buy-signal expansion.

## Experiment Grid

Config:

- `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- market: CN stock
- period: 2015-01-05 through 2025-12-31
- factor source: `daily_basic_public_risk_filter_bridge`
- horizon: 20
- execution lag: 1
- rebalance: 5 and 10
- top N diagnostic: 100
- cost: 10 bps plus 20 bps market impact
- max participation: 1% ADV
- liquidity floor for risk-filter portfolio: entry amount >= 10,000,000
- regime lookback: 120
- precomputed factor rows: 25,249,353

Grid result:

- cases: 6
- completed: 6
- failed: 0
- accepted direct long-only factors: 0

## Direct Long-Only Diagnostic

Direct TopN use remained rejected.

| Case | Total | Annual | Sharpe | Win | Max DD | Rank IC | Rank IC t | Relative | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `risk_filter_bridge_agreement_20`, top100, reb10 | 30.69% | 1.81% | 0.2200 | 48.28% | -25.53% | 0.0808 | 8.39 | -2343.05% | rejected |
| `risk_filter_bridge_equal_20`, top100, reb10 | 28.41% | 1.77% | 0.2153 | 48.89% | -24.83% | 0.0810 | 7.40 | -2345.34% | rejected |
| `risk_filter_bridge_anti_obv_weighted_20`, top100, reb10 | 26.04% | 1.55% | 0.1958 | 46.70% | -23.39% | 0.0782 | 8.09 | -2347.71% | rejected |

Interpretation:

- Cross-sectional IC is real and significant.
- The top tail still does not convert into a profitable direct long-only factor.
- The factor is only worth evaluating as bottom-tail exclusion.

## Bottom-Exclusion Overlay Audit

Shared settings:

- bottom exclusion: bottom 20%
- horizon: 20
- execution lag: 1

### Rebalance 5

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_agreement_20` | bottom-exclusion candidate | 0.0021 | 0.0042 | -0.0062 | 0.0021 | 8.46 | 70.34% | 65.63% | -99.56% |
| `risk_filter_bridge_anti_obv_weighted_20` | bottom-exclusion candidate | 0.0021 | 0.0042 | -0.0064 | 0.0021 | 7.84 | 67.49% | 75.51% | -99.66% |
| `risk_filter_bridge_equal_20` | bottom-exclusion candidate | 0.0021 | 0.0041 | -0.0060 | 0.0020 | 6.89 | 64.83% | 69.04% | -99.62% |

### Rebalance 10

| Factor | Class | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate | Kept Compound | Bottom Compound |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_agreement_20` | bottom-exclusion candidate | 0.0028 | 0.0049 | -0.0056 | 0.0021 | 6.33 | 70.34% | 47.41% | -92.45% |
| `risk_filter_bridge_anti_obv_weighted_20` | bottom-exclusion candidate | 0.0028 | 0.0051 | -0.0062 | 0.0023 | 6.03 | 68.82% | 56.36% | -94.19% |
| `risk_filter_bridge_equal_20` | bottom-exclusion candidate | 0.0028 | 0.0049 | -0.0055 | 0.0021 | 5.16 | 64.64% | 50.40% | -93.31% |

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
| `risk_filter_bridge_anti_obv_weighted_20` | research lead | 21.97% | -7.84% | 29.81% | 0.1168 | 0.0630 | -62.54% | 45.52% | 10/11 | 0 |
| `risk_filter_bridge_agreement_20` | research lead | 21.19% | -7.84% | 29.03% | 0.1126 | 0.0614 | -63.10% | 45.20% | 9/11 | 0 |
| `risk_filter_bridge_equal_20` | research lead | 20.51% | -7.84% | 28.35% | 0.1114 | 0.0604 | -62.92% | 44.78% | 9/11 | 0 |

### Rebalance 10

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_anti_obv_weighted_20` | research lead | 23.44% | -8.86% | 32.30% | 0.0920 | 0.0686 | -61.93% | 46.83% | 10/11 | 0 |
| `risk_filter_bridge_equal_20` | research lead | 20.63% | -8.86% | 29.48% | 0.0867 | 0.0645 | -62.30% | 46.20% | 9/11 | 0 |
| `risk_filter_bridge_agreement_20` | research lead | 20.53% | -8.86% | 29.39% | 0.0859 | 0.0641 | -63.51% | 46.53% | 10/11 | 0 |

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Risk-filter research leads:

- `risk_filter_bridge_anti_obv_weighted_20`
- `risk_filter_bridge_agreement_20`
- `risk_filter_bridge_equal_20`

Rejected or hibernated directions:

- direct long-only use of all bridge factors,
- more parameter expansion around the bridge before solving absolute risk quality,
- promotion based on relative return alone,
- single-family or two-filter risk filtering without industry/size decomposition.

## Interpretation

The bridge improved the diagnostic layer but not the investable layer.

Positive evidence:

- The bottom bucket is consistently bad.
- Overlay t-stat remains strong across rebalance 5 and 10.
- Costed portfolio relative return is positive in 9-10 of 11 yearly folds.
- No capacity-limited trades after the 10m liquidity floor.

Blocking evidence:

- Absolute Sharpe stays near 0.09-0.12.
- Overlap-adjusted Sharpe stays near 0.06-0.07.
- Max drawdown remains around -62%.
- Win rate remains below 47%.
- The benchmark used in bottom-exclusion portfolio is itself negative, so relative return is not enough.

This is not a profitable factor yet. It is a useful warning signal that still needs a better portfolio construction layer or a different alpha family.

## Engineering Audit

Round57 also exposed a process bottleneck:

- direct grid precomputed 25,249,353 factor rows once;
- each overlay and portfolio audit then recomputed the same matrix;
- the repeated precompute consumed several minutes and roughly 10-13GB memory per run.

Next runs should reuse the factor matrix, labels, and filtered bars across direct grid, overlay, and portfolio audits.

## Next Direction

Stop expanding the risk-filter bridge as a standalone family.

Round58 should rotate to an industry/size-neutral public formula and price-volume anomaly replay:

- use explainable public factors rather than more tuning of the same bridge;
- run industry-neutral and size-neutral IC before portfolio backtests;
- require costed portfolio evidence with absolute drawdown and overlap Sharpe gates;
- add shared precomputed factor-matrix/label reuse for multi-audit rounds;
- keep cumulative multiple-testing accounting active.
