# Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations without live trading.

## Tushare Token

Set the token in your shell or an ignored `.env` workflow:

```powershell
$env:TUSHARE_TOKEN="your-token"
```

Do not commit real tokens.

## Optional Dependency Install

Real Tushare and Parquet storage are optional until you are ready. When you decide to connect the API, install the optional data and parquet dependencies:

```powershell
python -m pip install -e ".[data,parquet]"
```

Then set `TUSHARE_TOKEN` and run the readiness checks below.

## Offline Ingest Smoke Test

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

## Tushare-Shaped Fixture Ingest

This exercises the Tushare daily ingest pipeline, manifest resume, raw storage, processed storage, and quality report without requiring a real token:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare-fixture --market CN --start-date 2024-01-02 --end-date 2024-01-06 --output-dir data\processed\tushare_fixture
```

When Tushare is installed and `TUSHARE_TOKEN` is set, switch `--source tushare-fixture` to `--source tushare`.

Adjusted close is calculated as `close * adj_factor` when adjustment factors are available. The ingest pipeline intentionally does not divide by the latest factor inside the requested range, because that makes a historical adjusted close depend on the end date of the request.

## Readiness Check

Before running a real Tushare smoke test:

```powershell
$env:PYTHONPATH='src'
python scripts\check_readiness.py
```

## Safe Tushare Smoke Plan

The smoke command is dry-run by default. It checks readiness and prints whether a real Tushare ingest is blocked or ready. Dry-run does not download data.

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_smoke.py --start-date 2024-01-02 --end-date 2024-01-06 --output-dir data\raw\tushare_smoke
```

After `tushare`, a Parquet engine, and `TUSHARE_TOKEN` are ready, add `--execute` to actually call Tushare:

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_smoke.py --start-date 2024-01-02 --end-date 2024-01-06 --output-dir data\raw\tushare_smoke --execute
```

## TradingView CSV Import

Export chart data from TradingView, then normalize the CSV shape:

```powershell
$env:PYTHONPATH='src'
python scripts\import_tradingview_csv.py input.csv data\raw\tradingview\parsed.csv
```
