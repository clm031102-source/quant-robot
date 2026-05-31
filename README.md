# Quant Robot

Local multi-market quantitative research framework for A-shares, A-share ETFs, Hong Kong stocks, US stocks, and crypto.

Phase one is research-only. It does not connect to real broker accounts, does not place live orders, and does not implement automatic trading.

## What Works In Phase One

- Canonical asset abstraction for CN, CN_ETF, HK, US, and CRYPTO.
- Offline fixture data for all research markets, including A-share ETFs.
- Unified OHLCV normalization with timezone-aware UTC timestamps.
- Parquet storage abstraction, enabled when `pyarrow` or `fastparquet` is installed.
- Implemented adapter paths for Tushare A-shares, yfinance HK/US, and ccxt crypto. AKShare and Tushare ETF fetching remain planned; A-share ETF research currently uses local CSV or fixture data.
- Basic factors: momentum, reversal, volatility, volume change, and liquidity.
- Forward-return labels with explicit execution lag.
- IC, Rank IC, quantile group returns, and long-short returns.
- Research backtest with explicit execution lag, holding period, portfolio scope, transaction cost assumptions, and conservative sleeve scaling for multi-day holding periods.
- Research-only signal snapshots, risk-capped target weights, and advisory rebalance plans.
- Local paper trading simulation with simulated intents, fills, cash, positions, equity curve, and China-market 100-share lot rounding.
- Research decision-risk layer with benchmark comparison, cash comparison, optional regime filtering, walk-forward relative-return gates, and paper drawdown guards.
- CSV, JSON, and SVG report outputs.

## Run Tests

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
```

## Run Core Checks

This runs the local test suite, Python compile check, project audit, readiness check, provider status, data catalog, offline fixture research, the configurable research pipeline, the experiment grid, walk-forward validation, signal snapshot generation, and paper simulation. It does not download market data.

The batch experiment grid exits non-zero if any case fails or if no case completes. Walk-forward validation exits non-zero if the underlying train/test grids fail or if no candidate is accepted. This keeps local checks from hiding failed research runs inside CSV/JSON leaderboards.

```powershell
$env:PYTHONPATH='src'
python scripts\run_checks.py --execute
```

To inspect the check plan without running it:

```powershell
$env:PYTHONPATH='src'
python scripts\run_checks.py
```

## Run Project Audit

```powershell
$env:PYTHONPATH='src'
python scripts\run_project_audit.py
```

Outputs are written to `data/reports/project_audit/`.

## Show Provider Status

```powershell
$env:PYTHONPATH='src'
python scripts\show_provider_status.py
```

This reports optional package, token, and implementation readiness for Tushare, AKShare, yfinance, ccxt, and Parquet storage.

## Show Local Data Catalog

```powershell
$env:PYTHONPATH='src'
python scripts\show_data_catalog.py --root data
```

## Run Offline Fixture Research

```powershell
$env:PYTHONPATH='src'
python scripts\run_fixture_research.py
```

Outputs are written to `data/reports/fixture_research/`.

## Run Configurable Research Pipeline

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source fixture --market ALL --factor momentum_2 --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline
```

`--market ALL` uses one global portfolio by default so the combined multi-market backtest is not accidentally leveraged once per market. Single-market runs use market-level selection by default. `--forward-horizon` drives both the forward-return label horizon and the research backtest holding period. Use `--portfolio-scope` or `--periods-per-year` only when you need to override the defaults.

When real processed bars exist, point the same pipeline at a processed-bars root:

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_fixture --market CN --factor momentum_2 --output-dir data\reports\research_pipeline_cn
```

## Run Batch Experiment Grid

This runs a local multi-market factor sweep and writes a leaderboard. Fixture results are explicitly marked as `data_mode=fixture` and are not real performance.

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --source fixture
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
python scripts\run_walk_forward.py --source fixture
```

Outputs are written to `data/reports/walk_forward/` by default:

- `walk_forward_leaderboard.csv`
- `walk_forward_leaderboard.json`
- `manifest.json`
- `train/` and `test/` per-case artifacts

Edit `configs/walk_forward.json` to change the split date, candidate grid, acceptance thresholds, and output path. The test segment includes train-period warmup bars for rolling factor calculation, but signals and trades are restricted to dates after the split.

## Run Signal Snapshot

This generates the latest research signal targets and a research-only advisory rebalance plan. It does not connect to a broker, read a real account, or place orders. If no positions CSV is supplied, the run assumes an empty local paper portfolio.

```powershell
$env:PYTHONPATH='src'
python scripts\run_signal_snapshot.py --source fixture --market ALL --factor momentum_2 --top-n 2 --max-asset-weight 0.4 --min-cash-weight 0.1
```

Outputs are written to `data/reports/signal_snapshot/` by default:

- `targets.csv`
- `rebalance_plan.csv`
- `manifest.json`

`targets.csv` is the strategy target state. `rebalance_plan.csv` is explicitly marked `executable=false` and is only an advisory bridge toward later simulated trading.

## Run Paper Simulation

This runs a local simulated trading loop from factor signals. It creates research-only intents, simulated fills, positions, and an equity curve. It does not connect to a broker, does not read a real account, and does not place orders.

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source fixture --market ALL --factor momentum_2 --top-n 2 --start-date 2024-01-04 --end-date 2024-01-12 --initial-cash 100000 --max-asset-weight 0.4 --min-cash-weight 0.1
```

Outputs are written to `data/reports/paper_simulation/` by default:

- `intents.csv`
- `fills.csv`
- `positions.csv`
- `equity_curve.csv`
- `snapshots.csv`
- `manifest.json`

Use `--max-drawdown-guard` and `--guard-cooldown-periods` when you want the local simulator to block new buy intents after a drawdown breach.

## Phase 2.6 Decision Risk Layer

Phase 2.6 adds benchmark/cash comparison, optional regime filtering, decision summaries, walk-forward relative-return and drawdown gates, and paper-simulation drawdown guards.

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source fixture --market CN_ETF --factor momentum_2 --top-n 1 --benchmark-asset-id CN_ETF_XSHG_510300 --cash-annual-return 0.015 --regime-filter --regime-lookback 3 --min-relative-return 0 --max-drawdown-limit 0.25
```

See `docs/phase_2_6_decision_risk.md` for output fields and interpretation rules.

## A-Share ETF Research

The framework includes a dedicated `CN_ETF` market and a default ETF universe in `configs/universe_cn_etf.yaml`. You can import TradingView ETF CSV exports into processed bars:

```powershell
$env:PYTHONPATH='src'
python scripts\import_etf_csv.py path\to\510300.csv --symbol 510300.SH --output-dir data\processed\etf_csv
```

The importer checks that a six-digit code in the CSV filename matches `--symbol`, uses an import lock to avoid concurrent year-partition rewrites, and does not count weekends as missing dates unless a real exchange calendar is provided later.
Its quality report checks missing rows across observed business days, so weekday gaps in CSV exports are flagged while weekend gaps are ignored.

Then run ETF-only research, factor mining, and paper simulation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\etf_csv --market CN_ETF --factor momentum_2 --top-n 2
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf.json --source processed-bars --data-root data\processed\etf_csv
python scripts\run_paper_simulation.py --source processed-bars --data-root data\processed\etf_csv --market CN_ETF --factor momentum_2 --top-n 2
```

## Run Local GUI

The local GUI is research-only and uses clearly labeled demo fixture data unless you explicitly wire in a real data workflow later.

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Open `http://127.0.0.1:8765` in your browser.

The GUI includes dashboard, data center, factor research, backtest report, signal snapshot, paper simulation, risk monitor, and logs/report views. Signal snapshots expose target weights and an advisory rebalance plan marked `executable=false`; the paper simulation view uses local demo bars by default and produces simulated fills only.

## Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations for Tushare A-share data and TradingView CSV verification. The first implementation is offline-testable and keeps all live data dependencies optional.

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

Real Tushare A-share access uses `TUSHARE_TOKEN` from the environment. Never commit a real token. Tushare ETF daily fetching is intentionally not marked ready until its ETF endpoint is wired and tested; use the `CN_ETF` CSV importer for ETF research now.

Tushare adjustment factors are stored as range-stable adjusted closes using `close * adj_factor` when adjustment factors are available. The pipeline avoids normalizing by the latest factor inside the requested date range because that would make the same historical date change when you request a longer range.

Before switching to real Tushare data, check optional dependencies and credentials:

```powershell
$env:PYTHONPATH='src'
python scripts\check_readiness.py
```

To test the Tushare-shaped pipeline without credentials:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare-fixture --market CN --output-dir data\processed\tushare_fixture
```

## No-Live-Trading Boundary

This repository intentionally has no real broker adapter, no order placement, no account login, and no automatic live execution. Later phases should extend from research signals to portfolio targets, then to simulated order intents, and only then to a carefully gated broker adapter.
