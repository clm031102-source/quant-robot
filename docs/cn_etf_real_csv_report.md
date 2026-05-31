# CN ETF Real CSV Research Report

Generated from local TradingView daily CSV files. This is research-only output: no broker connection, no order placement, and no live trading.

## Data Ingest

- Source: TradingView daily CSV exports.
- Raw directory: `data/raw/tradingview_etf_csv`.
- Processed directory: `data/processed/etf_csv`.
- Symbols imported: `510300.SH`, `510500.SH`, `512100.SH`, `512690.SH`, `512880.SH`, `515790.SH`, `516160.SH`, `588000.SH`, `159819.SZ`, `159915.SZ`.
- Rows imported: 21,798.
- Date range: 2011-12-09 to 2026-05-22.
- Duplicate `asset_id/date` rows: 0.
- Missing OHLCV values: 0.

## Sample-In Research Grid

Config: `configs/experiment_grid_cn_etf.json`.

Top sample-in candidate before costs:

- `CN_ETF_volatility_2_top1_cost0`
- Total return: 7.6243
- Annualized return: 0.1678
- Sharpe: 0.6246
- Max drawdown: -0.5139

However, all 5 bps cost variants in the first grid were negative. The current short-window daily strategies are highly turnover-sensitive.

## Walk-Forward Validation

Config: `configs/walk_forward_cn_etf.json`, split date `2023-01-03`.

Accepted candidates: 5 of 12.

Best walk-forward candidate:

- `CN_ETF_volatility_2_top1_cost0`
- Test total return: 0.6302
- Test Sharpe: 0.6119
- Test max drawdown: -0.3766
- Stability score: 0.5998

All tested 5 bps cost variants were rejected because out-of-sample Sharpe dropped below zero.

## Paper Simulation

Candidate: `volatility_2`, `top_n=1`.

Risk constraints:

- Initial cash: 100,000 CNY.
- Commission: 5 bps.
- Slippage: 5 bps.
- Max asset weight: 40%.
- Min cash weight: 10%.

Result:

- Ending equity: 55,926.78 CNY.
- Total return: -0.4405.
- Annualized return: -0.0409.
- Sharpe: -0.2371.
- Max drawdown: -0.6204.

## Current Conclusion

The local ETF research pipeline is now usable on real CSV data. The first real-data run rejects the naive short-window daily turnover strategy under realistic costs. The next research step should focus on reducing turnover before considering any simulated deployment: longer lookbacks, weekly/monthly rebalance schedules, holding-period constraints, volatility/risk filters, and cash or benchmark comparison.

## Low-Turnover Follow-Up

Added `rebalance_interval` support to the research pipeline, experiment grid, walk-forward validation, and paper simulation. When `periods_per_year` is not explicitly supplied, annualization now scales by market periods divided by the rebalance interval, so sparse 5-day or 10-day signal series are not mislabeled as daily return series.

Config: `configs/experiment_grid_cn_etf_low_turnover.json`.

- Cases: 40.
- Completed: 40.
- Failed: 0.
- Factors: `momentum_20`, `momentum_60`, `reversal_20`, `volatility_20`, `liquidity_20`.
- Rebalance intervals: 5 and 10 trading days.
- Forward horizon: 5 trading days.
- Costs: 5 and 10 bps.

Best sample-in candidate after corrected annualization:

- `CN_ETF_volatility_20_top1_cost5_reb5`
- Total return: 0.6188.
- Annualized return: 0.0354.
- Sharpe: 0.5290.
- Max drawdown: -0.1919.
- Turnover: 0.20.

Walk-forward config: `configs/walk_forward_cn_etf_low_turnover.json`, split date `2023-01-03`.

Best walk-forward candidate:

- `CN_ETF_momentum_20_top2_cost5_reb5`
- Test total return: 0.0660.
- Test Sharpe: 0.3434.
- Test max drawdown: -0.1160.
- Test trades: 324.

Risk-constrained paper simulation for the best walk-forward candidate:

- Candidate: `momentum_20`, `top_n=2`, `rebalance_interval=5`.
- Costs: 5 bps commission and 5 bps slippage.
- Max asset weight: 40%.
- Min cash weight: 10%.
- Ending equity from 100,000 CNY: 291,898.54 CNY.
- Total return: 1.9202.
- Corrected annualized return: 0.0805.
- Corrected Sharpe: 0.4651.
- Max drawdown: -0.5554.

Updated conclusion: the lower-turnover path is materially better than the first short-window daily strategies, but the drawdown is still too large and the out-of-sample Sharpe is not strong enough for live trading.

Phase 2.6 now adds the next research gate: benchmark/cash comparison, optional benchmark-momentum regime filtering, walk-forward relative-return and drawdown thresholds, and a paper-simulation drawdown guard that blocks new buy intents during cooldown. The stronger ETF universe expansion remains a separate data task.
