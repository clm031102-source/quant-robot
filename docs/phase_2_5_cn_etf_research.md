# Phase 2.5 CN ETF Research

This phase adds A-share ETF research readiness without live trading.

It supports `CN_ETF` as a dedicated research market that shares China exchange calendars, CNY currency, and Asia/Shanghai timezone, while keeping ETF assets separate from individual A-shares.

## What Is Ready

- Default CN ETF universe in `configs/universe_cn_etf.yaml`.
- Demo ETF fixture bars in the same unified market-data schema.
- TradingView ETF CSV import into local processed bars.
- Factor research, experiment grid, walk-forward validation, signal snapshots, and paper simulation with `market=CN_ETF`.
- Import safety checks for filename/symbol mismatch and a local import lock to prevent concurrent partition rewrites.
- Paper simulation rounds A-share ETF fills to 100-share lots.
- Local GUI market selection for A股 ETF.

## Import TradingView ETF CSV

Export daily ETF data from TradingView, then run:

```powershell
$env:PYTHONPATH='src'
python scripts\import_etf_csv.py path\to\510300.csv --symbol 510300.SH --output-dir data\processed\etf_csv
```

Import additional ETF CSVs into the same output root. The importer merges symbols into the same `CN_ETF` year partition instead of replacing the whole ETF dataset. Run imports one at a time; the importer creates `.import_etf_csv.lock` and refuses to run if another import is already active.

Use filenames that contain the ETF code, such as `510300.csv` or `510300_1D.csv`. If the filename code conflicts with `--symbol`, the import fails instead of silently labeling the data as the wrong ETF.

For multiple TradingView exports, put the raw files in one folder and run the batch importer:

```powershell
$env:PYTHONPATH='src'
python scripts\batch_import_etf_csv.py --input-dir . --raw-dir data\raw\tradingview_etf_csv --output-dir data\processed\etf_csv --move-raw
```

The batch importer infers `.SH`/`.SZ` from TradingView filenames such as `SSE_DLY_510300, 1D_xxx.csv` and `SZSE_DLY_159915, 1D_xxx.csv`, moves them into stable project filenames like `510300_SH_1d.csv`, then writes a `batch_import_manifest.json`.

## Run ETF Research

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\etf_csv --market CN_ETF --factor momentum_2 --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline_cn_etf
```

## Run ETF Factor Mining Grid

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf.json --source processed-bars --data-root data\processed\etf_csv
```

For the lower-turnover research path, run the dedicated grid. It uses longer factor windows, 5-day holding, 5/10-day rebalance intervals, and realistic transaction costs:

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf_low_turnover.json --source processed-bars --data-root data\processed\etf_csv
```

When `periods_per_year` is left unset, the pipeline scales annualization by the rebalance interval. For example, a 5-day rebalance interval uses roughly `252 / 5` periods per year rather than pretending each return is daily.

## Run ETF Walk-Forward Validation

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_cn_etf.json --source processed-bars --data-root data\processed\etf_csv
```

Lower-turnover walk-forward validation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_cn_etf_low_turnover.json --source processed-bars --data-root data\processed\etf_csv
```

## Run ETF Paper Simulation

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source processed-bars --data-root data\processed\etf_csv --market CN_ETF --factor momentum_2 --top-n 2 --initial-cash 100000 --max-asset-weight 0.4 --min-cash-weight 0.1
```

## Safety Boundary

This phase still does not connect to brokers, does not read a real account, and does not place orders. Paper simulation fills are local simulated records only.

Tushare ETF fetching is not marked implemented yet. When the Tushare ETF endpoint is wired and tested, `CN_ETF` can move from planned provider support to direct provider ingestion.
