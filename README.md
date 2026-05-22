# Quant Robot

Local multi-market quantitative research framework for A-shares, Hong Kong stocks, US stocks, and crypto.

Phase one is research-only. It does not connect to real broker accounts, does not place live orders, and does not implement automatic trading.

## What Works In Phase One

- Canonical asset abstraction for CN, HK, US, and CRYPTO.
- Offline fixture data for all four markets.
- Unified OHLCV normalization with timezone-aware UTC timestamps.
- Parquet storage abstraction, enabled when `pyarrow` or `fastparquet` is installed.
- Data adapter interfaces for AKShare, Tushare, yfinance, and ccxt.
- Basic factors: momentum, reversal, volatility, volume change, and liquidity.
- Forward-return labels with explicit execution lag.
- IC, Rank IC, quantile group returns, and long-short returns.
- Research backtest with next-date execution and transaction cost assumptions.
- CSV, JSON, and SVG report outputs.

## Run Tests

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

## Run Offline Fixture Research

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_fixture_research.py
```

Outputs are written to `data/reports/fixture_research/`.

## Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations for Tushare A-share data and TradingView CSV verification. The first implementation is offline-testable and keeps all live data dependencies optional.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

Real Tushare access uses `TUSHARE_TOKEN` from the environment. Never commit a real token.

## No-Live-Trading Boundary

This repository intentionally has no real broker adapter, no order placement, no account login, and no automatic live execution. Later phases should extend from research signals to portfolio targets, then to simulated order intents, and only then to a carefully gated broker adapter.
