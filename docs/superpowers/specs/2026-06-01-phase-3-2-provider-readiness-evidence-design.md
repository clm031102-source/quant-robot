# Phase 3.2 Provider Readiness Evidence Design

## Purpose

Phase 3.2 converts coarse provider-readiness blockers into local, reviewable evidence. The goal is to make optional package, token, adapter, market coverage, and Parquet readiness visible without crossing any external API boundary.

## Scope

The feature reads local provider status only. It does not install packages, fetch market data, call provider APIs, validate token permissions, connect to brokers, read accounts, or place orders.

Out of scope:

- Dependency installation.
- Provider API calls.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.ops.provider_evidence` owns pure evidence logic. It accepts a provider-status payload and returns:

- summary counts;
- provider rows with a normalized `readiness_status`;
- provider/market coverage rows;
- Parquet readiness evidence;
- Markdown output.

`scripts/run_provider_evidence.py` owns filesystem concerns. It reads an optional `provider_status.json`, otherwise builds status from the current environment, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` runs provider evidence immediately after provider status so local checks capture both raw readiness and review-ready evidence.

`quant_robot.ops.evidence_refresh` recommends the provider evidence command before generic readiness/status commands whenever provider readiness blocks review.

## Readiness Labels

- `ready`: package, token, and adapter implementation are available.
- `missing_dependency`: optional dependency is missing.
- `missing_token`: required token or credential is missing.
- `missing_dependency_and_token`: dependency and token are both missing.
- `planned_adapter`: provider adapter is planned but not implemented.
- `blocked`: provider is not ready for another local reason.

## Testing

Use unittest:

- `tests/unit/test_provider_evidence.py`
- `tests/unit/test_provider_evidence_cli.py`
- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
