# Phase 4.3 Data Gap Ledger Board Integration Design

## Purpose

Phase 4.3 connects the Phase 4.2 data-gap resolution ledger to the pre-API readiness board. The goal is to make unresolved data-gap rows visible in the main blocker register and action queue, not just in a standalone ledger artifact.

## Scope

The feature reads local JSON artifacts only. It does not resolve gaps, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic gap remediation.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.pre_api_readiness_board` accepts an optional `data_gap_resolution` payload. When provided, it adds a `data_gap_resolution` readiness item based on `blocking_gap_rows` and `blocks_api_boundary` from the ledger summary.

The board blocker register maps blocking gap rows to `data_gap_resolution_blocking_gaps` with `scripts/run_data_gap_resolution.py` as the recommended local command.

`scripts/run_pre_api_readiness_board.py` reads the default ledger path `data/reports/data_gap_resolution/data_gap_resolution_ledger.json` when it exists and passes it into the board builder. Its CLI also accepts `--data-gap-resolution` for explicit local artifact selection.

## Testing

Use unittest:

- `tests/unit/test_pre_api_readiness_board.py`
- `tests/unit/test_pre_api_readiness_board_cli.py`

Full verification requires artifact regeneration and `scripts/run_checks.py --execute`.
