# Multi-Market Quant Research Framework Design

## 1. Goal And Non-Goals

Build a local, reproducible Python framework for multi-market quantitative research across A-shares, Hong Kong stocks, US stocks, and crypto. Phase one is a research system: it ingests market data, normalizes it into a common schema, stores it as Parquet, computes basic factors, evaluates factor quality, and runs simple research backtests.

Phase one intentionally excludes live trading, broker login, automatic order placement, high-frequency trading, leverage, options, futures, and complex machine learning. The system should be built so those capabilities can be added later through clean interfaces, but no phase-one code should connect to real trading accounts or place orders.

The practical target is not to promise profit. The target is to build a reliable research machine that can discover, test, reject, compare, and reproduce factor ideas without hidden lookahead bias.

## 2. Architecture Principles

The framework is divided into bounded layers. Each layer has a stable contract and depends only on the layers below it.

```text
configs
  -> assets
  -> data adapters
  -> normalization
  -> parquet storage
  -> factor engine
  -> factor evaluation
  -> research backtest
  -> reports
```

Core principles:

- Research correctness beats trading cleverness in phase one.
- Every time-dependent operation must make the data availability timestamp explicit.
- Raw data, normalized data, factor data, labels, backtest results, and reports are stored separately.
- Market differences are modeled explicitly instead of hidden inside string parsing.
- Data source adapters are replaceable; research code never calls AKShare, Tushare, yfinance, or ccxt directly.
- The backtest engine consumes normalized data and portfolio targets only; it does not know about broker APIs.
- All phase-one behavior must be testable with tiny deterministic sample datasets.

## 3. Recommended Technical Stack

Use a small, boring stack that is strong for tabular time-series research:

- Python 3.11+
- pandas for tabular transformations
- numpy for numeric calculations
- pyarrow for Parquet IO
- pydantic for configuration and schema validation
- scipy for Spearman correlation where needed
- matplotlib for initial charts
- pytest for tests
- ruff for formatting and linting

Optional data libraries are kept behind adapters:

- AKShare for A-share, Hong Kong, and some US data
- Tushare for A-share data when the user provides a token
- yfinance for Hong Kong and US data
- ccxt for crypto OHLCV data

The package must still import and run tests without optional data-source libraries installed. Adapter modules should fail gracefully at runtime with clear messages if their optional dependency is missing.

## 4. Directory Structure

```text
quant_robot/
  pyproject.toml
  README.md
  .env.example
  configs/
    markets.yaml
    data_sources.yaml
    research.yaml
    backtest.yaml
  data/
    raw/
    processed/
    reports/
  docs/
    architecture.md
    no_lookahead.md
    superpowers/
      specs/
      plans/
  scripts/
    ingest_data.py
    run_factors.py
    run_factor_test.py
    run_backtest.py
  src/
    quant_robot/
      __init__.py
      assets/
        __init__.py
        models.py
        registry.py
        calendars.py
      data/
        __init__.py
        adapters/
          __init__.py
          base.py
          akshare_adapter.py
          tushare_adapter.py
          yfinance_adapter.py
          ccxt_adapter.py
        normalize.py
        quality.py
      storage/
        __init__.py
        parquet_store.py
        paths.py
      schema/
        __init__.py
        market_data.py
        factors.py
        backtest.py
      factors/
        __init__.py
        base.py
        technical.py
        pipeline.py
      research/
        __init__.py
        labels.py
        ic.py
        groups.py
        long_short.py
      backtest/
        __init__.py
        engine.py
        portfolio.py
        costs.py
        metrics.py
      reports/
        __init__.py
        plots.py
        tearsheet.py
      utils/
        __init__.py
        time.py
        logging.py
  tests/
    fixtures/
    unit/
    integration/
```

## 5. Phase-One Minimum Runnable Version

The first runnable version should complete one full research loop with local sample data before depending on live downloads.

Minimum behavior:

1. Define assets for four markets with the fields `symbol`, `market`, `exchange`, `asset_type`, `currency`, `timezone`, and `calendar`.
2. Load tiny deterministic OHLCV fixtures for each market.
3. Normalize all market data to a shared schema.
4. Store and read normalized bars as Parquet.
5. Compute basic factors: momentum, reversal, volatility, volume change, and liquidity.
6. Create forward-return labels with explicit horizon and execution lag.
7. Evaluate IC, Rank IC, quantile group returns, and long-short returns.
8. Run a simple research backtest from factor ranks.
9. Output metrics and chart images to `data/reports/`.
10. Include tests that prove the factor and backtest pipelines do not use future data.

After the fixture-driven loop works, live adapter smoke scripts can be added for real data sources.

## 6. Asset Model

The canonical asset model:

```text
asset_id: stable internal id, e.g. "CN_XSHG_600519"
symbol: source-facing symbol, e.g. "600519", "0700.HK", "AAPL", "BTC/USDT"
market: "CN", "HK", "US", "CRYPTO"
exchange: "XSHG", "XSHE", "XHKG", "XNYS", "XNAS", "BINANCE"
asset_type: "stock", "etf", "crypto_spot"
currency: "CNY", "HKD", "USD", "USDT"
timezone: IANA timezone
calendar: trading calendar id
name: display name
is_active: active flag for current asset registry
lot_size: minimum tradable unit
tick_size: price increment
```

`asset_id` is the internal join key. Research modules should not join on raw symbols because symbols differ by source and may change.

## 7. Market Data Schema

Normalized bar schema:

```text
asset_id
symbol
market
exchange
asset_type
timestamp
date
timezone
calendar
frequency
open
high
low
close
adj_close
volume
amount
vwap
currency
source
adjusted
ingested_at
```

Schema rules:

- `timestamp` is timezone-aware UTC.
- `date` is the local trading date for the asset's market.
- `adj_close` is used for return calculations when available.
- `close` remains the observed close from the source.
- `amount` is turnover in the quote currency when available.
- `vwap` is derived as `amount / volume` only when units are valid.
- Missing optional fields are represented as nulls, not fake zeroes.
- Duplicate `(asset_id, timestamp, frequency, source)` rows are rejected.

## 8. Parquet Storage Layout

Use partitioned Parquet paths:

```text
data/processed/bars/frequency=1d/market=CN/year=2025/part.parquet
data/processed/factors/frequency=1d/factor=momentum_20/market=US/year=2025/part.parquet
data/processed/labels/frequency=1d/horizon=5/market=HK/year=2025/part.parquet
data/processed/backtests/run_id=<run_id>/portfolio.parquet
data/reports/<run_id>/
```

Write behavior should be deterministic:

- Sort by `asset_id`, `timestamp`.
- Keep explicit partition columns in the dataframe.
- Avoid overwriting unrelated partitions.
- Use a manifest or metadata file per research run with config hash, data range, factor names, and generated time.

## 9. Data Source Adapter Design

Each adapter implements the same interface:

```text
supports(asset) -> bool
fetch_ohlcv(asset, start, end, frequency, adjustment) -> RawBarFrame
normalize(raw, asset, source) -> MarketDataFrame
```

Adapters:

- AKShare adapter: A-share, Hong Kong, selected US endpoints.
- Tushare adapter: A-share daily bars and adjustment factors, requires token.
- yfinance adapter: Hong Kong and US equities.
- ccxt adapter: crypto OHLCV from configured exchange.

The adapter layer is not trusted. All adapter output goes through normalization and schema validation before storage.

## 10. Market Difference Handling

A-shares:

- Currency: CNY.
- Timezone: Asia/Shanghai.
- Calendars: SSE and SZSE.
- Phase one models daily bars only.
- Later phases add ST flags, limit-up/limit-down, suspensions, delisted names, and point-in-time index constituents.

Hong Kong stocks:

- Currency: HKD.
- Timezone: Asia/Hong_Kong.
- Calendar: HKEX.
- Lot sizes and stamp duty matter for later trading stages.
- Phase one ignores intraday lunch breaks because daily data is used.

US stocks:

- Currency: USD.
- Timezone: America/New_York.
- Calendars: NYSE and NASDAQ.
- Split/dividend adjustment is important for historical return research.
- Phase one excludes premarket and after-hours sessions.

Crypto:

- Currency: quote currency such as USDT or USD.
- Timezone: UTC.
- Calendar: 24/7.
- Exchange is part of identity because BTC/USDT on two exchanges is not always identical.
- Phase one starts with daily OHLCV and no funding, futures, or perpetual swaps.

## 11. Factor Engine

Factor functions operate on normalized, sorted bars and return a long dataframe:

```text
date
timestamp
asset_id
market
factor_name
factor_value
lookback_window
created_at
```

Phase-one factors:

- Momentum: `adj_close / adj_close.shift(window) - 1`.
- Reversal: negative short-horizon return, e.g. `-(adj_close / adj_close.shift(5) - 1)`.
- Volatility: rolling standard deviation of daily returns.
- Volume change: `volume / rolling_mean(volume, window) - 1`.
- Liquidity: `amount / abs(return)` style Amihud-inspired measure with safe handling for zero returns.

Factor quality rules:

- All rolling windows use only current and past rows.
- Factors are computed per asset first, then cross-sectionally transformed per date.
- Cross-sectional ranking, winsorization, and z-scoring are done within `(date, market)` unless an explicit multi-market research mode is selected.
- Currency conversion is not included in phase-one factor calculations.

## 12. Labels And No-Lookahead Contract

Forward-return labels are separate from factors:

```text
date
asset_id
market
horizon
execution_lag
forward_return
entry_timestamp
exit_timestamp
```

Default label:

```text
signal generated after t close
entry at t+1 close for research simplicity
exit at t+1+horizon close
```

No-lookahead contract:

- Feature rows at date `t` can only read raw bars with local date `<= t`.
- Labels may read future prices, but labels are never passed into factor code.
- Backtest signals at `t` are executed no earlier than `t+1`.
- Any function that aligns features and labels must include `execution_lag`.
- Tests must include a sentinel future price spike and prove factor values before the spike do not change.

## 13. Factor Evaluation

Evaluation modules consume factors and labels:

- IC: Pearson correlation between factor value and forward return by date.
- Rank IC: Spearman correlation by date.
- Group returns: assign assets into quantiles by factor rank within market and date.
- Long-short returns: top quantile return minus bottom quantile return.

Outputs:

- Daily IC series.
- IC mean, standard deviation, information ratio, positive ratio.
- Quantile return table.
- Long-short equity curve.
- Turnover by quantile when portfolio memberships change.
- Coverage statistics: asset count and missing factor ratio per date.

## 14. Research Backtest Design

The phase-one backtest is a research backtest, not a trading simulator.

Inputs:

- Factor scores.
- Normalized bars.
- Asset registry.
- Cost model.
- Rebalance schedule.
- Portfolio construction rule.

Portfolio construction:

- Select top N or top quantile per market.
- Equal weight by default.
- Optional gross exposure cap per market.
- Cash is implicit.

Execution:

- Generate target weights at date `t`.
- Apply them using prices at `t+1` according to configured execution price.
- Default execution price is next close for robustness with daily bars.
- Costs are charged on turnover.

Metrics:

- Total return.
- Annualized return.
- Annualized volatility.
- Sharpe ratio.
- Max drawdown.
- Calmar ratio.
- Win rate.
- Turnover.
- Average number of holdings.

## 15. Reporting

Reports are intentionally simple and reproducible:

- `metrics.json`
- `equity_curve.parquet`
- `positions.parquet`
- `trades.parquet`
- `ic_timeseries.png`
- `quantile_returns.png`
- `long_short_curve.png`
- `backtest_equity_curve.png`
- `drawdown.png`

Every report directory includes a `run_config.json` file with the parameters used.

## 16. Error Handling And Data Quality

Validation checks:

- Required schema columns exist.
- Prices are non-negative.
- `high >= low`.
- `open`, `high`, `low`, `close` are internally consistent when all are present.
- Duplicate bars are rejected.
- Dates are monotonic per asset after sorting.
- Missing data coverage is reported.

Errors should fail fast during tests and be explicit during scripts. Silent coercion is not allowed for schema-critical fields.

## 17. Future Extension Path

Phase two: stronger backtesting

- More realistic execution assumptions.
- Market-specific costs.
- Rebalance calendars.
- Walk-forward testing.
- Parameter sweep tracking.
- Multi-factor combination.

Phase three: simulated trading robot

- Paper account state.
- Order intent generation.
- Simulated order matching.
- Scheduler.
- Logs and alerts.
- Daily health checks.

Phase four: small-capital live trading for one market

- One broker adapter.
- Read-only account sync first.
- Manual approval gate before orders.
- Kill switch.
- Position and order reconciliation.
- Secrets management.

Phase five: multi-strategy automation

- Strategy registry.
- Capital allocation.
- Risk dashboard.
- Cloud scheduler.
- Experiment database.

## 18. Risk Control Principles

- No real broker connection in phase one.
- No automatic order placement in phase one.
- No leverage in phase one.
- No high-frequency assumptions in phase one.
- Every strategy must be evaluated after costs.
- Every factor must report coverage and turnover.
- Sample periods must be split into research and validation windows.
- Promising factors must survive out-of-sample checks before paper trading.
- Paper trading must run before live trading.
- Live trading starts with small capital and a manual kill switch.

## 19. Completion Standard For Phase One

Phase one is complete when:

- A developer can run tests from a clean checkout.
- The package imports without optional data-source libraries installed.
- Fixture data for CN, HK, US, and CRYPTO flows through normalization, Parquet storage, factor computation, factor evaluation, research backtest, and report generation.
- The five basic factors are implemented and tested.
- IC, Rank IC, group returns, and long-short returns are implemented and tested.
- The research backtest produces deterministic metrics on fixture data.
- No-lookahead tests pass.
- The README explains how to run the local research loop.
- No code connects to real broker accounts or places real orders.
