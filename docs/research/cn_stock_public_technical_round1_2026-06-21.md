# CN Stock Public Technical Factor Round 1

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Round status: round 1 of the current 3-round review cycle
- Scope: CN A-share stock cross-sectional factors, not ETF rotation

## Purpose

This round moved factor mining away from single-family moneyflow search by adding a reusable public technical factor source. The first batch follows common public-market technical ideas with low parameter count and clear economic intuition:

- `rsi_reversal_14`
- `bollinger_reversal_20`
- `donchian_position_20`
- `macd_histogram_12_26_9`

## Implementation

- Added `public_technical` factor source with long-schema output and past-only calculations.
- Connected it to the research pipeline, experiment-grid precompute path, CLI factor-source choices, and project-audit factor registry.
- Added walk-forward config: `configs/walk_forward_cn_stock_public_technical_20260621.json`.
- Added fast long-cycle diagnostic config: `configs/experiment_grid_cn_stock_public_technical_fast_20260621.json`.

## Verification

- Public technical red-green tests passed.
- Research pipeline and experiment-grid precompute tests passed.
- Full unit discovery passed: 734 tests.
- Compileall passed for `src`, `scripts`, and `tests`.
- Project audit passed: summary, safety, factor registry, and temporal safety.
- Startup gate cleared and includes 3-round review plus 10-round GitHub sync governance.
- Token literal search found no Tushare token in `configs`, `docs`, `scripts`, `src`, or `tests`.

## Long-Cycle Fast Diagnostic

Command:

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_technical_fast_20260621.json --source authority-processed-bars --authority-bars-config configs\cn_stock_authority_bars_2015_2025.json --allow-review-required-data-manifest
```

Data manifest:

- Refreshed on 2026-06-21.
- Blockers: none.
- Warnings: `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars`.
- This public technical batch does not consume moneyflow inputs, but the warning is kept visible.

Result summary:

| factor | annualized return | Sharpe | overlap-adjusted Sharpe | max drawdown | win rate | mean rank IC | rank IC p-value | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `rsi_reversal_14` | 13.84% | 0.349 | 0.263 | -76.55% | 45.61% | 0.0467 | 2.50e-16 | rejected |
| `bollinger_reversal_20` | 25.54% | 0.219 | 0.198 | -75.62% | 45.68% | 0.0487 | 1.36e-19 | rejected |
| `donchian_position_20` | 14.90% | 0.183 | 0.165 | -80.76% | 51.14% | -0.0034 | 5.56e-01 | rejected |
| `macd_histogram_12_26_9` | 5.04% | 0.232 | 0.140 | -95.68% | 42.83% | -0.0385 | 4.83e-16 | rejected |

Rejection reasons:

- All 4 candidates were rejected.
- Dominant blockers: drawdown above limit, capacity-limited trades, relative return below threshold for RSI and MACD.
- Extreme trade return flags appeared, so raw total-return numbers must not be trusted as profitability evidence.

## Partial Walk-Forward Attempt

The full public-technical walk-forward config started but timed out after 30 minutes. It produced completed fold artifacts for folds 1-3 and a partial fold 4 train artifact under:

```text
data/reports/walk_forward_cn_stock_public_technical_20260621
```

Partial evidence:

- Completed rows inspected: 288.
- Rejection reasons counted from completed fold artifacts:
  - `relative_return_below_threshold`: 266
  - `capacity_limited_trades_present`: 222
  - `insufficient_oos_trades`: 48
- No promotable walk-forward evidence was found in the inspected partial artifacts.

## Interpretation

This round did not produce a tradable standalone factor. The useful finding is directional:

- Public mean-reversion indicators (`rsi_reversal_14`, `bollinger_reversal_20`) show statistically visible IC on the long cycle.
- That IC does not translate into a robust standalone top100 strategy under current portfolio construction.
- Capacity, drawdown, and extreme-return contamination are the binding issues.
- Trend/breakout indicators (`donchian_position_20`, `macd_histogram_12_26_9`) are not good standalone directions in this setup.

## Next Direction

Round 2 should not expand this public-technical grid blindly. It should test a smaller, more economic composite:

- Keep only RSI/Bollinger mean-reversion as candidate components.
- Add liquidity/capacity gates before ranking.
- Add data-quality or outlier guards before portfolio evaluation.
- Reject any candidate before walk-forward if fast long-cycle diagnostics show max drawdown worse than 50%, capacity-limited trades, or negative tail IC.
- Run a reduced walk-forward only after passing the fast gate.
