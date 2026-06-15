# Phase 4.8 Provider Remediation Board Integration Design

## Purpose

Phase 4.8 connects the provider remediation matrix to the pre-API readiness board. The goal is to make dependency, credential, adapter, and storage remediation counts visible in the main blocker board instead of leaving them in a separate local report.

## Scope

The feature reads local provider-remediation artifacts and augments the local readiness board. It remains research-only.

Out of scope:

- Installing optional provider packages.
- Creating or storing provider tokens.
- Calling market-data providers.
- Connecting to brokers.
- Reading accounts.
- Placing orders.
- Enabling live trading.

## Architecture

`quant_robot.ops.pre_api_readiness_board` accepts an optional `provider_remediation` payload. When present, it adds a `provider_remediation` readiness item after provider readiness with evidence from the remediation summary:

- remediation item count;
- dependency item count;
- credential item count;
- adapter item count;
- storage dependency item count.

The item blocks API-boundary planning when `summary.remediation_items > 0` or `summary.blocks_api_boundary` is true. The blocker register maps this item to `provider_remediation_items_open` and recommends `scripts/run_provider_remediation.py`.

`scripts/run_pre_api_readiness_board.py` reads `data/reports/provider_remediation/provider_remediation_matrix.json` by default when it exists, accepts `--provider-remediation` for explicit local artifact selection, and passes the payload into the builder.

## Testing

Use unittest:

- `tests/unit/test_pre_api_readiness_board.py`
- `tests/unit/test_pre_api_readiness_board_cli.py`

The builder test must prove that a remediation matrix adds the readiness item, blocker, and local action. The CLI test must prove that an explicit provider-remediation JSON file is loaded and written into board artifacts.

Full verification requires regenerating real pre-API readiness artifacts and running `scripts/run_checks.py --execute`.
