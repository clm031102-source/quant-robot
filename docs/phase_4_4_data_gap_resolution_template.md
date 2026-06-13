# Phase 4.4 Data Gap Resolution Template

Phase 4.4 makes the data-gap resolution process fillable.

It remains research-only. It does not classify gaps automatically, call providers, backfill files, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Fillable `gap_resolutions_template.csv` generated from the current ledger.
- `data_gap_resolution_status_options.csv` documenting supported statuses and whether each status blocks future API-boundary planning.
- Template helper functions in `quant_robot.ops.data_gap_resolution`.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

New output files:

- `gap_resolutions_template.csv`
- `data_gap_resolution_status_options.csv`

## How The Template Is Used

The template contains one row per gap with stable `gap_id`, asset metadata, default `needs_review`, blank `evidence_note`, blank reviewer fields, allowed statuses, and local review guidance.

After local evidence is recorded, the template can be fed back into the ledger:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --resolution-file data\reports\data_gap_resolution\gap_resolutions_template.csv --output-dir data\reports\data_gap_resolution
```

Rows with `needs_review` or `backfill_required` continue to block API-boundary planning. Rows with `accepted_non_trading_day`, `accepted_suspension_or_no_trade`, or `resolved_with_backfill` stop blocking only for that specific gap.

Phase 4.5 validates this CSV on input. Unknown `gap_id`, unsupported `resolution_status`, and duplicate `gap_id` rows are reported in `data_gap_resolution_validation.csv` and ignored until corrected.
