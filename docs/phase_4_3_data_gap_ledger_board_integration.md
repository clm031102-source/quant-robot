# Phase 4.3 Data Gap Ledger Board Integration

Phase 4.3 connects the data-gap resolution ledger to the pre-API readiness board.

It remains research-only. It does not resolve data automatically, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- `data_gap_resolution` input support in `quant_robot.ops.pre_api_readiness_board`.
- Default CLI loading of `data/reports/data_gap_resolution/data_gap_resolution_ledger.json`.
- A board readiness item for unresolved ledger rows.
- A blocker ID: `data_gap_resolution_blocking_gaps`.
- A local action queue command for `scripts/run_data_gap_resolution.py`.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Explicit ledger path:

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --data-gap-resolution data\reports\data_gap_resolution\data_gap_resolution_ledger.json --output-dir data\reports\pre_api_readiness_board
```

## Interpretation

When the data-gap ledger has `blocking_gap_rows > 0` or `blocks_api_boundary=true`, the readiness board marks `data_gap_resolution` as `block`.

This means the project now has a closed local loop:

- Phase 3.1 finds exact missing dates.
- Phase 4.2 tracks row-level resolution status.
- Phase 4.3 exposes unresolved rows on the main readiness board.
