# Phase 4.14 Residual Data Gap Review Pack

Phase 4.14 turns the data-gap rows that remain blocking after rehearsal into a focused local review pack.

It remains research-only. It does not mutate the real ledger, import external data, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Residual review builder in `quant_robot.ops.residual_data_gap_review`.
- CLI artifact generation through `scripts/run_residual_data_gap_review.py`.
- Core-check integration after `residual_blocker_focus`.
- Residual data-gap row CSV for the rows still blocking after rehearsal.
- A fillable `residual_gap_review_template.csv` that can be passed back to `scripts/run_data_gap_resolution.py --resolution-file`.
- A local action queue for audit, local CSV refresh, ledger application, rehearsal refresh, projection refresh, and focus refresh.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_data_gap_review.py --output-dir data\reports\residual_data_gap_review
```

Output files:

- `residual_data_gap_review_pack.json`
- `residual_data_gap_review_pack.md`
- `residual_data_gap_rows.csv`
- `residual_gap_review_template.csv`
- `residual_gap_action_queue.csv`
- `residual_gap_status_options.csv`

## Interpretation

This pack is a residual review worksheet. It starts from the rehearsal result rather than the baseline ledger, so rows cleared by the rehearsal sample do not appear in the residual list.

Use `residual_gap_review_template.csv` to record local evidence for the remaining blocking gaps, then apply it with:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --resolution-file data\reports\residual_data_gap_review\residual_gap_review_template.csv --output-dir data\reports\data_gap_resolution
```

The pack preserves the API boundary as blocked while residual rows remain.
