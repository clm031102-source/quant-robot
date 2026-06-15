# Phase 4.12 Pre-API Readiness Projection Pack Design

## Purpose

Phase 4.12 consolidates current readiness evidence with rehearsal projections. The goal is to show, in one local artifact, how much the data-gap and provider-remediation rehearsals reduce blockers and which blocker classes remain before any API-boundary planning can start.

## Scope

The feature reads local reports and writes local projection artifacts. It does not modify real evidence, install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Applying rehearsal rows to real ledgers.
- Treating rehearsal rows as actual review approvals.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.ops.readiness_projection` owns pure projection logic. It accepts:

- `pre_api_readiness_board.json`;
- `data_gap_rehearsal.json`;
- `provider_remediation_rehearsal.json`.

It emits:

- current and projected readiness items;
- blocker delta rows by track;
- residual blocker rows by track;
- safety and live-boundary status;
- Markdown summary.

The projection updates only tracks with explicit rehearsal projections:

- `data_gap_resolution`;
- `provider_remediation`.

All other readiness-board tracks remain unchanged. This keeps the artifact honest: it shows projected reductions without implying actual evidence changed.

`scripts/run_readiness_projection.py` owns filesystem concerns. It reads default local artifacts, writes JSON/Markdown/CSV outputs, and prints a compact summary.

`scripts/run_checks.py` includes the projection after `pre_api_readiness_board` and before `blocker_worklist`, so it sees refreshed board state and refreshed rehearsal packs.

## Artifacts

- `readiness_projection_pack.json`
- `readiness_projection_pack.md`
- `readiness_projection_items.csv`
- `readiness_projection_deltas.csv`
- `readiness_projection_residuals.csv`

## Testing

Use unittest:

- `tests/unit/test_readiness_projection.py`
- `tests/unit/test_readiness_projection_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires regenerating real projection artifacts and running `scripts/run_checks.py --execute`.
