# Phase 4.5 Data Gap Resolution Validation

Phase 4.5 makes local resolution CSV inputs auditable.

It remains research-only. It does not accept evidence automatically, backfill data, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- `resolution_validation` summary inside `data_gap_resolution_ledger.json`.
- `data_gap_resolution_validation.csv`.
- Reporting for:
  - unknown `gap_id` rows;
  - unsupported `resolution_status` rows;
  - duplicate `gap_id` rows.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --resolution-file data\reports\data_gap_resolution\gap_resolutions_template.csv --output-dir data\reports\data_gap_resolution
```

Output file:

- `data_gap_resolution_validation.csv`

## Interpretation

Invalid, unknown, or duplicate rows are local review errors. They are reported and ignored. The ledger keeps the first valid row for a gap and leaves unresolved or invalid rows as blocking evidence until the resolution file is corrected.

The current generated template still has every row as `needs_review`, so validation should show zero errors while the ledger remains blocked by six unresolved gaps.
