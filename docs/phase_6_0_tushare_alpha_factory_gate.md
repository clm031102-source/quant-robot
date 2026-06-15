# Phase 6.0 Tushare Alpha Factory Gate

## What Changed

Phase 6.0 adds a local-only gate for the real-data alpha research chain:

1. Tushare OHLCV ingest
2. Tushare `daily_basic` factor-input ingest
3. Daily-basic Alpha Factory
4. Multiple-testing corrected candidate decision

The gate writes:

- `data/reports/tushare_alpha_factory_gate/tushare_alpha_factory_gate_pack.json`
- `data/reports/tushare_alpha_factory_gate/tushare_alpha_factory_gate_pack.md`
- `data/reports/tushare_alpha_factory_gate/tushare_alpha_factory_gate_stage_ledger.csv`
- `data/reports/tushare_alpha_factory_gate/tushare_alpha_factory_gate_next_actions.csv`

## Current Status

Current readiness is blocked because `TUSHARE_TOKEN` is not set in the process, user, machine, or local ignored `.env` file.

Parquet support is ready.

The fixture execute path completed end-to-end:

- OHLCV ingest completed.
- `daily_basic` factor-input ingest completed.
- Alpha Factory completed.
- Adjusted significant candidates: `0`
- Status: `no_adjusted_significant_alpha`
- Paper candidate allowed: `false`
- Live boundary allowed: `false`

This is the expected conservative behavior: no candidate enters paper validation unless it survives multiple-testing correction.

## Commands

Token setup with ignored `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

Or set the token in the current shell:

```powershell
$env:TUSHARE_TOKEN="<your-token>"
```

Readiness:

```powershell
$env:PYTHONPATH='src'
python scripts\check_readiness.py
```

Real alpha-factory gate:

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_alpha_factory_gate.py --source tushare --market CN --start-date 2024-01-02 --end-date 2024-12-31 --report-dir data\reports\tushare_alpha_factory_gate --data-root data\processed\tushare_alpha_factory_gate --execute
```

Fixture proof:

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_alpha_factory_gate.py --source tushare-fixture --market CN --start-date 2024-01-02 --end-date 2024-01-12 --report-dir data\reports\tushare_alpha_factory_gate_fixture --data-root data\processed\tushare_alpha_factory_gate_fixture --execute
```

## Boundary

This stage is research-to-paper only. It does not connect to a broker, read account data, place orders, approve live trading, or weaken the adjusted IC gate.

If candidates survive, the next stage is paper-only batch replay and promotion review. Live trading remains blocked until separate live-boundary and small-capital validation gates are satisfied.

Paper batch for adjusted-significant Alpha Factory candidates:

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_batch.py --config configs\paper_batch_tushare_alpha_factory.json
```
