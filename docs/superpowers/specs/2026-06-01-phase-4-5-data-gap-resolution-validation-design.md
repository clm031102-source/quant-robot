# Phase 4.5 Data Gap Resolution Validation Design

## Purpose

Phase 4.5 makes local data-gap resolution inputs auditable. The goal is to report invalid statuses, unknown gap IDs, and duplicate resolution rows when a reviewer feeds a CSV back into `scripts/run_data_gap_resolution.py --resolution-file`.

## Scope

The feature validates local CSV rows only. It does not decide whether a gap is resolved, backfill data, call providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic evidence acceptance.
- Automatic data remediation.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.data_gap_resolution` adds validation while indexing resolution rows:

- known gap IDs come from the current missing-date rows;
- unknown `gap_id` rows are reported and ignored;
- invalid `resolution_status` rows are reported and ignored;
- duplicate `gap_id` rows are reported and the first valid local row is kept;
- the ledger gains a `resolution_validation` payload with summary counts and detailed rows.

`write_data_gap_resolution_ledger()` writes `data_gap_resolution_validation.csv` alongside the ledger, template, and status options.

The CLI keeps the same interface. Validation appears only when local resolution rows are provided.

## Testing

Use unittest:

- `tests/unit/test_data_gap_resolution.py`
- `tests/unit/test_data_gap_resolution_cli.py`

Full verification requires a sample invalid resolution file, artifact regeneration, and `scripts/run_checks.py --execute`.
