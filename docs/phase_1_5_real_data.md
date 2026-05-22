# Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations without live trading.

## Tushare Token

Set the token in your shell or an ignored `.env` workflow:

```powershell
$env:TUSHARE_TOKEN="your-token"
```

Do not commit real tokens.

## Offline Ingest Smoke Test

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

## TradingView CSV Import

Export chart data from TradingView, then normalize the CSV shape:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\import_tradingview_csv.py input.csv data\raw\tradingview\parsed.csv
```
