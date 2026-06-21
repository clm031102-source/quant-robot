# CN Stock Bottom-Exclusion Portfolio Round 52 - 2026-06-21

## Purpose

Round51 found that two public price-volume formula factors may be useful as bottom-quantile exclusion signals rather than direct TopN buy signals.

Round52 converts that diagnostic into a costed, benchmark-aware portfolio test:

- frozen formulas,
- frozen bottom 20% exclusion,
- 20-day forward horizon,
- execution lag 1,
- rebalance intervals 5 and 10,
- cost 10 bps,
- market impact 20 bps,
- max participation 1% ADV,
- portfolio value 1,000,000,
- liquidity floor: entry amount at least 10,000,000.

The benchmark is the same broad equal-weight universe after the same liquidity floor and cost assumptions.

## Tooling Added

Reusable vectorized backtest:

- `src/quant_robot/ops/bottom_exclusion_portfolio_backtest.py`

Runner:

- `scripts/run_bottom_exclusion_portfolio_backtest.py`

Tests:

- `tests/unit/test_bottom_exclusion_portfolio_backtest.py`
- `tests/unit/test_bottom_exclusion_portfolio_backtest_cli.py`

Classification was deliberately tightened:

- positive relative return alone is only `research_lead_risk_filter`,
- `costed_risk_filter_candidate` requires positive total return, positive relative return, sufficient positive relative folds, overlap-adjusted Sharpe at least 0.5, max drawdown no worse than -50%, and no capacity violations.

## Commands

rebalance=5:

```powershell
python scripts\run_bottom_exclusion_portfolio_backtest.py `
  --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json `
  --rebalance-interval 5 `
  --holding-period 20 `
  --cost-bps 10 `
  --market-impact-bps 20 `
  --max-participation-rate 0.01 `
  --min-entry-amount 10000000 `
  --portfolio-value 1000000 `
  --output-dir data\reports\bottom_exclusion_portfolio_public_formula_round52_20260621_reb5_liquid10m
```

rebalance=10:

```powershell
python scripts\run_bottom_exclusion_portfolio_backtest.py `
  --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json `
  --rebalance-interval 10 `
  --holding-period 20 `
  --cost-bps 10 `
  --market-impact-bps 20 `
  --max-participation-rate 0.01 `
  --min-entry-amount 10000000 `
  --portfolio-value 1000000 `
  --output-dir data\reports\bottom_exclusion_portfolio_public_formula_round52_20260621_reb10_liquid10m
```

## Results

### Rebalance 5, Liquid 10m

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_volume_contraction_reversal_20` | research lead | 136.74% | 64.98% | 71.76% | 0.3213 | 0.1823 | -53.51% | 47.98% | 11/11 | 0 |
| `formula_pv_corr_reversal_20` | research lead | 111.83% | 64.98% | 46.85% | 0.2872 | 0.1604 | -56.52% | 48.14% | 10/11 | 0 |
| `formula_range_contraction_breakout_20` | research lead, weak priority | 76.99% | 64.98% | 12.01% | 0.2290 | 0.1271 | -60.04% | 47.98% | 8/11 | 0 |

Summary:

- Costed candidates: 0
- Research leads: 3
- Capacity-limited candidates: 0
- Best overlap-adjusted Sharpe: 0.1823
- Best relative return: 71.76%

### Rebalance 10, Liquid 10m

| Factor | Class | Total | Benchmark | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Relative Folds | Capacity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_volume_contraction_reversal_20` | research lead | 123.81% | 55.12% | 68.68% | 0.1871 | 0.1424 | -55.17% | 50.84% | 11/11 | 0 |
| `formula_pv_corr_reversal_20` | research lead | 105.66% | 55.12% | 50.54% | 0.1722 | 0.1297 | -56.76% | 50.50% | 11/11 | 0 |
| `formula_range_contraction_breakout_20` | research lead, weak priority | 65.82% | 55.12% | 10.70% | 0.1334 | 0.1001 | -60.87% | 49.83% | 8/11 | 0 |

Summary:

- Costed candidates: 0
- Research leads: 3
- Capacity-limited candidates: 0
- Best overlap-adjusted Sharpe: 0.1424
- Best relative return: 68.68%

## Interpretation

This is not a profitable deployable strategy.

What improved:

- bottom-exclusion produces positive relative return against the broad equal-weight benchmark,
- the effect persists across every annual fold for `volume_contraction` and nearly every fold for `pv_corr`,
- the 10m liquidity floor removes capacity violations.

What still fails:

- overlap-adjusted Sharpe is far below 0.5,
- max drawdown is worse than -50% for all rows,
- win rate is near 50% or below,
- absolute annualized return is modest after costs,
- the strategy still carries broad-market drawdown risk.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads:

1. `formula_volume_contraction_reversal_20` as a bottom-exclusion risk filter.
2. `formula_pv_corr_reversal_20` as a weaker bottom-exclusion risk filter.

Low priority / likely stop:

- `formula_range_contraction_breakout_20`; Round51 overlay t-stat was weak and Round52 relative improvement is too small.

## Next Step

Round53 must be a three-round review, not more mining:

- audit Rounds 51-52 against Round49 failure,
- decide whether to keep bottom-exclusion only as a risk overlay,
- decide whether price-volume public formulas should be hibernated,
- rotate the next mining family unless a risk-control overlay with regime/cash protection can be pre-registered without tuning,
- preserve the useful reusable tooling and stop calling these factors profitable.
