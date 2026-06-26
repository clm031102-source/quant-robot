# CN Stock Daily-Basic Residual Bottom-Exclusion Round 54 - 2026-06-21

## Purpose

Round53 required a family rotation away from public price-volume formulas.

Round54 re-used the existing daily-basic residual composite family because it already had clean long-cycle RankIC evidence from Round11 and a public economic rationale:

- value,
- low turnover,
- low downside/tail risk,
- residualization against size, liquidity, and momentum exposures.

The test used the new Round51/Round52 translation path:

1. bottom-exclusion overlay audit,
2. costed broad-basket risk-filter backtest,
3. liquidity floor before capacity judgment,
4. strict candidate classification.

## Overlay Audit

### Rebalance 5

| Factor | Class | Dates | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | bottom-exclusion candidate | 530 | 0.0046 | 0.0054 | 0.0014 | 0.0008 | 4.14 | 0.59 |
| `resid_value_reversal_low_tail_20` | bottom-exclusion candidate | 530 | 0.0051 | 0.0058 | 0.0024 | 0.0007 | 3.09 | 0.59 |
| `resid_value_quality_low_vol_20` | weak/unproven | 530 | 0.0049 | 0.0048 | 0.0051 | -0.0001 | -0.24 | 0.50 |

### Rebalance 10

| Factor | Class | Dates | Full Mean | Kept Mean | Bottom Mean | Overlay | t-stat | Positive Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | bottom-exclusion candidate | 265 | 0.0053 | 0.0061 | 0.0020 | 0.0008 | 3.09 | 0.58 |
| `resid_value_reversal_low_tail_20` | bottom-exclusion candidate | 265 | 0.0057 | 0.0065 | 0.0025 | 0.0008 | 2.67 | 0.60 |
| `resid_value_quality_low_vol_20` | weak/unproven | 265 | 0.0056 | 0.0055 | 0.0057 | -0.0000 | -0.13 | 0.49 |

## Costed Portfolio Validation

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
| `resid_value_low_turnover_quality_20` | research lead | 40.12% | 26.32% | 13.80% | 0.1504 | 0.0826 | -63.57% | 48.16% | 9/11 | 0 |
| `resid_value_reversal_low_tail_20` | weak/unproven | 47.57% | 35.10% | 12.47% | 0.1668 | 0.0914 | -63.95% | 47.87% | 6/11 | 0 |
| `resid_value_quality_low_vol_20` | weak/unproven | 31.52% | 32.42% | -0.91% | 0.1400 | 0.0763 | -62.84% | 48.18% | 6/11 | 0 |

### Rebalance 10

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | research lead | 37.59% | 23.56% | 14.03% | 0.1008 | 0.0748 | -64.16% | 49.05% | 8/11 | 0 |
| `resid_value_reversal_low_tail_20` | research lead | 44.77% | 30.83% | 13.94% | 0.1101 | 0.0817 | -64.21% | 49.11% | 7/11 | 0 |
| `resid_value_quality_low_vol_20` | weak/unproven | 28.33% | 29.30% | -0.97% | 0.0968 | 0.0723 | -64.10% | 48.52% | 6/11 | 0 |

## Interpretation

This family is weaker than the price-volume bottom-exclusion lead.

Useful:

- `resid_value_low_turnover_quality_20` has repeatable bottom-tail separation.
- `resid_value_reversal_low_tail_20` has weaker but visible bottom-tail separation.
- Capacity is clean after the 10m liquidity floor.

Not useful enough:

- overlap-adjusted Sharpe is below 0.10,
- max drawdown is around -64%,
- absolute total return is low versus the risk taken,
- annual relative folds are weaker than the price-volume exclusion lead,
- `resid_value_quality_low_vol_20` does not work as bottom exclusion.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads:

- `resid_value_low_turnover_quality_20`, weak risk-filter component only.
- `resid_value_reversal_low_tail_20`, lower-priority weak component.

Hibernate:

- standalone residual composite TopN,
- standalone residual composite bottom-exclusion broad basket,
- `resid_value_quality_low_vol_20` as bottom-exclusion signal.

## Next Direction

Do not spend another round rerunning daily-basic residual composites.

Round55 should implement or pre-register a more explicit smart-money / quality / low-vol proxy family with no intraday look-ahead:

- volume-price efficiency,
- close-location value with volume confirmation,
- downside-volatility and liquidity quality,
- daily-basic value/turnover context,
- strict liquidity floor from the start.

The new family should be evaluated first with IC/quantile/bottom-exclusion diagnostics before any full portfolio budget.
