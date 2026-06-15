# Phase 4.4 Data Gap Resolution Template Design

## Purpose

Phase 4.4 makes the data-gap resolution process fillable. The goal is to generate a local CSV template and status-option reference from the Phase 4.2 ledger so each missing ETF date can be reviewed, annotated, and fed back into `scripts/run_data_gap_resolution.py --resolution-file`.

## Scope

The feature writes local template artifacts only. It does not classify gaps automatically, backfill data, call providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic trading-calendar decisions.
- Automatic data remediation.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.data_gap_resolution` adds template helpers built from ledger rows:

- `build_resolution_template_rows()` returns one fillable row per gap with stable `gap_id`, asset metadata, default `needs_review`, blank evidence/reviewer fields, and local guidance.
- `resolution_status_options()` returns supported statuses with blocking semantics and short descriptions.
- `write_data_gap_resolution_ledger()` writes two new artifacts: `gap_resolutions_template.csv` and `data_gap_resolution_status_options.csv`.

`scripts/run_data_gap_resolution.py` keeps the same command interface. Running it produces the ledger plus the fillable template and status reference.

## Testing

Use unittest:

- `tests/unit/test_data_gap_resolution.py`
- `tests/unit/test_data_gap_resolution_cli.py`

Full verification requires regenerating the real data-gap artifacts and running `scripts/run_checks.py --execute`.
