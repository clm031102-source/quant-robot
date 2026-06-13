# Phase 4.7 Provider Remediation Matrix Design

## Purpose

Phase 4.7 turns provider-readiness evidence into a local remediation matrix. The goal is to identify each missing package, missing token, planned adapter, and Parquet dependency blocker with a clear local verification command and review hint.

## Scope

The feature reads local provider evidence artifacts and writes local remediation reports. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic package installation.
- Automatic token creation or secret storage.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.

## Architecture

`quant_robot.ops.provider_remediation` owns pure remediation logic. It accepts `provider_evidence_pack.json` and emits:

- one remediation item per provider blocker;
- one remediation item for Parquet storage readiness when needed;
- blocker-type counts;
- research-only safety text;
- Markdown output.

`scripts/run_provider_remediation.py` owns filesystem concerns. It reads the provider evidence pack, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the remediation matrix immediately after `provider_evidence`.

## Testing

Use unittest:

- `tests/unit/test_provider_remediation.py`
- `tests/unit/test_provider_remediation_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires regenerating real provider-remediation artifacts and running `scripts/run_checks.py --execute`.
