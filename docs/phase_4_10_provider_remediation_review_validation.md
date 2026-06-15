# Phase 4.10 Provider Remediation Review Validation

Phase 4.10 validates provider-remediation review rows and applies valid local statuses back into the remediation matrix.

It remains research-only. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Optional `--review-file` input for `scripts/run_provider_remediation.py`.
- `provider_remediation_validation.csv`.
- `review_validation` summary in `provider_remediation_matrix.json`.
- Review-status fields on each remediation item.
- `blocking_remediation_items` in the provider-remediation summary.
- Readiness-board logic that blocks on blocking remediation items, not total historical remediation rows.

## CLI Usage

Generate a fresh template:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Apply a filled review file:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --review-file data\reports\provider_remediation\provider_remediation_review_template.csv --output-dir data\reports\provider_remediation
```

Output files include:

- `provider_remediation_matrix.json`
- `provider_remediation_validation.csv`
- `provider_remediation_review_template.csv`
- `provider_remediation_status_options.csv`

## Validation Rules

Invalid review rows are reported and ignored:

- unknown `remediation_id`;
- unsupported `review_status`;
- duplicate `remediation_id` after the first valid row.

Valid review rows update the matching remediation item with review status, evidence note, reviewer, reviewed timestamp, and provider-readiness blocking state.

The current generated template defaults to `needs_review`, so the real provider-remediation board remains blocked until local review evidence records non-blocking statuses such as `resolved_locally` or `accepted_out_of_scope`.
