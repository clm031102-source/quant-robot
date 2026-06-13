# Phase 4.6 Data Gap Resolution Rehearsal Design

## Purpose

Phase 4.6 adds a local rehearsal for data-gap resolution. The goal is to prove, with generated local artifacts, how a valid resolution CSV changes the data-gap ledger's blocking counts before reviewers edit the real resolution file.

## Scope

The feature creates rehearsal-only artifacts. It does not mutate the real resolution template, classify real gaps, backfill data, call providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic evidence acceptance.
- Automatic data remediation.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.data_gap_rehearsal` owns pure rehearsal logic. It reads a data-quality audit, builds the baseline data-gap ledger, creates sample local resolution rows for the first N gaps, builds a rehearsed ledger from those rows, and reports before/after blocking counts.

`scripts/run_data_gap_rehearsal.py` owns filesystem concerns. It reads `data_quality_gap_audit.json`, writes JSON/Markdown/CSV artifacts under `data/reports/data_gap_rehearsal`, and prints a compact summary.

`scripts/run_checks.py` includes the rehearsal immediately after `data_gap_resolution` so the full local check chain proves both the real ledger and a controlled replay path.

## Testing

Use unittest:

- `tests/unit/test_data_gap_rehearsal.py`
- `tests/unit/test_data_gap_rehearsal_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires regenerating real rehearsal artifacts and running `scripts/run_checks.py --execute`.
