# Phase 4.6 Data Gap Resolution Rehearsal

Phase 4.6 generates a local rehearsal pack for data-gap resolution.

It remains research-only. It does not accept real evidence, backfill data, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Rehearsal builder in `quant_robot.ops.data_gap_rehearsal`.
- CLI artifact generation through `scripts/run_data_gap_rehearsal.py`.
- Core-check integration immediately after `data_gap_resolution`.
- Sample resolution CSV rows that show how a valid resolution file changes blocking counts.
- A readiness projection for the `data_gap_resolution` track.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_rehearsal.py --output-dir data\reports\data_gap_rehearsal
```

Optional sample size:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_rehearsal.py --sample-size 2 --output-dir data\reports\data_gap_rehearsal
```

Output files:

- `data_gap_rehearsal.json`
- `data_gap_rehearsal.md`
- `sample_gap_resolutions.csv`
- `rehearsed_data_gap_rows.csv`
- `data_gap_rehearsal_summary.csv`

## Interpretation

The rehearsal marks the first N gaps as `accepted_non_trading_day` with explicit rehearsal-only evidence. It then rebuilds a temporary ledger and compares blocking counts before and after the sample rows.

These artifacts are not real approvals. They are a local dry run proving that the resolution pipeline, validation, ledger counts, and readiness projection respond to valid resolution rows.
