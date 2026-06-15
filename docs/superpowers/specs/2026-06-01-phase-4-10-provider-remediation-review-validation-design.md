# Phase 4.10 Provider Remediation Review Validation Design

## Purpose

Phase 4.10 lets the provider-remediation review template feed back into the local remediation matrix. The goal is to validate local review rows, apply supported review statuses to matching remediation items, and expose blocking counts that the pre-API readiness board can use.

## Scope

The feature validates local CSV review evidence only. It does not install packages, set tokens, validate secrets, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic package installation.
- Automatic token or secret checks.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.provider_remediation.build_provider_remediation_matrix()` accepts optional `review_rows`. It validates each row against current `remediation_id` values and supported statuses:

- unknown `remediation_id`;
- unsupported `review_status`;
- duplicate `remediation_id`.

Only valid first rows are applied. Each remediation item receives:

- `review_status`;
- `evidence_note`;
- `reviewed_by`;
- `reviewed_at`;
- updated `blocks_provider_readiness`.

The matrix includes `review_validation` with summary counts and validation rows. The summary adds review-status counts and `blocking_remediation_items`; `blocks_api_boundary` is true only when blocking remediation items remain.

`write_provider_remediation_matrix()` writes `provider_remediation_validation.csv`.

`scripts/run_provider_remediation.py` accepts `--review-file`, reads CSV rows locally, and passes them into the builder.

`quant_robot.ops.pre_api_readiness_board` treats provider remediation as blocking based on `blocks_api_boundary` or `blocking_remediation_items`, not merely the total number of remediation rows. This lets non-blocking review statuses clear the provider-remediation track without deleting evidence rows.

## Testing

Use unittest:

- `tests/unit/test_provider_remediation.py`
- `tests/unit/test_provider_remediation_cli.py`
- `tests/unit/test_pre_api_readiness_board.py`

The pure test must prove valid review rows are applied and invalid rows are reported. The CLI test must prove `--review-file` writes validation CSV. The board test must prove a non-blocking provider-remediation summary can clear the provider-remediation readiness item.

Full verification requires regenerating real provider-remediation artifacts and running `scripts/run_checks.py --execute`.
