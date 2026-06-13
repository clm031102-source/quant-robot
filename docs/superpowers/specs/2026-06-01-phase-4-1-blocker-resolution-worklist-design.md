# Phase 4.1 Blocker Resolution Worklist Design

## Purpose

Phase 4.1 turns the pre-API readiness board into a concrete local worklist. The goal is to map every blocker to an open work item and a local-only command so the project can close blockers methodically before any future API-boundary planning.

## Scope

The feature reads the local readiness board only. It does not run remediation, call providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic remediation.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.blocker_worklist` owns pure worklist logic. It accepts a pre-API readiness board and returns:

- open work item rows;
- deduplicated local action queue;
- live-boundary state;
- Markdown output.

`scripts/run_blocker_worklist.py` owns filesystem concerns. It reads `pre_api_readiness_board.json`, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the worklist after the readiness board so the full local check chain ends with an actionable work queue.

## Testing

Use unittest:

- `tests/unit/test_blocker_worklist.py`
- `tests/unit/test_blocker_worklist_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
