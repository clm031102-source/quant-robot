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
