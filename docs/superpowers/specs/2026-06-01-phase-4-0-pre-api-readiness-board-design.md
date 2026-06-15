# Phase 4.0 Pre-API Readiness Board Design

## Purpose

Phase 4.0 turns Phase 3 evidence packs into one local readiness board. The goal is to give operators a single artifact that shows whether the project is still blocked, why, which local commands come next, and whether broker/account/order boundaries remain disabled.

## Scope

The feature reads local evidence artifacts only. It does not call providers, install packages, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.
- Provider API calls.
- Automatic remediation.

## Architecture

`quant_robot.ops.pre_api_readiness_board` owns pure aggregation logic. It accepts promotion review, data quality, provider evidence, paper observation, duplicate registry, manual review rehearsal, and evidence refresh payloads, then returns:

- overall status;
- readiness item rows;
- blocker register rows;
- next local actions;
- live-boundary state;
- Markdown output.

`scripts/run_pre_api_readiness_board.py` owns filesystem concerns. It reads the default local reports, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the board after Evidence Refresh so the full local check chain ends with one consolidated operational status.

## Testing

Use unittest:

- `tests/unit/test_pre_api_readiness_board.py`
- `tests/unit/test_pre_api_readiness_board_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
