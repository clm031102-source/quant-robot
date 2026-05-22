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
- Research backtest with explicit execution lag, holding period, portfolio scope, and transaction cost assumptions.
- CSV, JSON, and SVG report outputs.

## Run Tests

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

## Run Core Checks

This runs the local test suite, Python compile check, project audit, readiness check, provider status, data catalog, offline fixture research, the configurable research pipeline, the experiment grid, and walk-forward validation. It does not download market data.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_checks.py --execute
```

To inspect the check plan without running it:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_checks.py
```

## Run Project Audit

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_project_audit.py
```

Outputs are written to `data/reports/project_audit/`.

## Show Provider Status

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\show_provider_status.py
```

This reports optional package and token readiness for Tushare, AKShare, yfinance, ccxt, and Parquet storage.

## Show Local Data Catalog

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\show_data_catalog.py --root data
```

## Run Offline Fixture Research

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_fixture_research.py
```

Outputs are written to `data/reports/fixture_research/`.

## Run Configurable Research Pipeline

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_research_pipeline.py --source fixture --market ALL --factor momentum_2 --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline
```

`--market ALL` uses one global portfolio by default so the combined multi-market backtest is not accidentally leveraged once per market. Single-market runs use market-level selection by default. `--forward-horizon` drives both the forward-return label horizon and the research backtest holding period. Use `--portfolio-scope` or `--periods-per-year` only when you need to override the defaults.

When real processed bars exist, point the same pipeline at a processed-bars root:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_fixture --market CN --factor momentum_2 --output-dir data\reports\research_pipeline_cn
```

## Run Batch Experiment Grid

This runs a local multi-market factor sweep and writes a leaderboard. Fixture results are explicitly marked as `data_mode=fixture` and are not real performance.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_experiment_grid.py --source fixture
```

Outputs are written to `data/reports/experiment_grid/` by default:

- `leaderboard.csv`
- `leaderboard.json`
- `manifest.json`
- one artifact folder per experiment case

Edit `configs/experiment_grid.json` to change markets, factors, transaction costs, position counts, holding horizon, optional portfolio scope, annualization periods, ranking metric, and output path. Factor names such as `momentum_2` must reference windows included in `factor_windows`; mismatches fail fast instead of producing silent no-trade cases.

## Run Walk-Forward Validation

This splits local data into train and out-of-sample test periods, runs the same experiment candidates on both sides, and ranks candidates by sample-out stability. Fixture results remain demo-only.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_walk_forward.py --source fixture
```

Outputs are written to `data/reports/walk_forward/` by default:

- `walk_forward_leaderboard.csv`
- `walk_forward_leaderboard.json`
- `manifest.json`
- `train/` and `test/` per-case artifacts

Edit `configs/walk_forward.json` to change the split date, candidate grid, acceptance thresholds, and output path. The test segment includes train-period warmup bars for rolling factor calculation, but signals and trades are restricted to dates after the split.

## Run Local GUI

The local GUI is research-only and uses clearly labeled demo fixture data unless you explicitly wire in a real data workflow later.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_gui.py
```

Open `http://127.0.0.1:8765` in your browser.

## Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations for Tushare A-share data and TradingView CSV verification. The first implementation is offline-testable and keeps all live data dependencies optional.

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

Real Tushare access uses `TUSHARE_TOKEN` from the environment. Never commit a real token.

Tushare adjustment factors are stored as range-stable adjusted closes using `close * adj_factor` when adjustment factors are available. The pipeline avoids normalizing by the latest factor inside the requested date range because that would make the same historical date change when you request a longer range.

Before switching to real Tushare data, check optional dependencies and credentials:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\check_readiness.py
```

To test the Tushare-shaped pipeline without credentials:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\ingest_data.py --source tushare-fixture --market CN --output-dir data\processed\tushare_fixture
```

## No-Live-Trading Boundary

This repository intentionally has no real broker adapter, no order placement, no account login, and no automatic live execution. Later phases should extend from research signals to portfolio targets, then to simulated order intents, and only then to a carefully gated broker adapter.
