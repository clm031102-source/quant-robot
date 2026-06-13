# Phase 4.2 Data Gap Resolution Ledger Design

## Purpose

Phase 4.2 turns the Phase 3.1 missing-date audit into a row-level resolution ledger. The goal is to make every missing asset/date traceable to a local decision status, evidence note, and next local command before any future API-boundary planning.

## Scope

The feature reads local data-quality audit artifacts and optional local resolution notes. It does not backfill data automatically, call data providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic data remediation.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.data_gap_resolution` owns pure ledger logic. It accepts a data-quality gap audit plus optional resolution rows and returns:

- stable gap IDs for every asset/date row;
- default `needs_review` status for unresolved gaps;
- override support from a local CSV;
- blocker counts and API-boundary state;
- local action queue;
- Markdown output.

`scripts/run_data_gap_resolution.py` owns filesystem concerns. It reads `data_quality_gap_audit.json`, optionally reads a local resolution CSV, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the ledger immediately after the data-quality audit so the core check chain moves from detecting gaps to tracking their resolution.

## Testing

Use unittest:

- `tests/unit/test_data_gap_resolution.py`
- `tests/unit/test_data_gap_resolution_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
