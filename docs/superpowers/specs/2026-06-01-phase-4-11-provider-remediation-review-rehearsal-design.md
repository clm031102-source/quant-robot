# Phase 4.11 Provider Remediation Review Rehearsal Design

## Purpose

Phase 4.11 rehearses provider-remediation review rows without changing real provider-readiness evidence. The goal is to prove that the Phase 4.10 review-validation pipeline can reduce provider-remediation blockers when local review rows mark out-of-current-scope providers as non-blocking.

## Scope

The feature writes rehearsal-only artifacts. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Applying rehearsal rows to real remediation evidence.
- Automatic dependency installation.
- Automatic token handling.
- Provider downloads or network calls.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.ops.provider_remediation_rehearsal` owns pure rehearsal logic. It accepts a provider-evidence pack, builds a baseline provider-remediation matrix, generates sample review rows for out-of-current-scope providers, applies those rows through `build_provider_remediation_matrix(..., review_rows=...)`, and emits before/after blocker counts.

Default out-of-current-scope providers are:

- `akshare`
- `ccxt`
- `yfinance`

The current CN ETF candidate still leaves `tushare` and `parquet` blockers untouched because resolving those requires real local package/credential/storage changes.

`scripts/run_provider_remediation_rehearsal.py` owns filesystem concerns. It reads `provider_evidence_pack.json`, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the rehearsal immediately after `provider_remediation`.

## Artifacts

- `provider_remediation_rehearsal.json`
- `provider_remediation_rehearsal.md`
- `sample_provider_remediation_reviews.csv`
- `rehearsed_provider_remediation_items.csv`
- `provider_remediation_rehearsal_summary.csv`

## Testing

Use unittest:

- `tests/unit/test_provider_remediation_rehearsal.py`
- `tests/unit/test_provider_remediation_rehearsal_cli.py`
- `tests/unit/test_check_plan.py`

Full verification requires regenerating real rehearsal artifacts and running `scripts/run_checks.py --execute`.
