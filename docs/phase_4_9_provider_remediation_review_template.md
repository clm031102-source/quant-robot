# Phase 4.9 Provider Remediation Review Template

Phase 4.9 turns provider-remediation rows into a fillable local review template.

It remains research-only. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- `provider_remediation_review_template.csv`
- `provider_remediation_status_options.csv`
- Pure template helper: `build_review_template_rows()`
- Pure status helper: `remediation_status_options()`

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Output files now include:

- `provider_remediation_matrix.json`
- `provider_remediation_matrix.md`
- `provider_remediation_items.csv`
- `provider_remediation_summary.csv`
- `provider_remediation_review_template.csv`
- `provider_remediation_status_options.csv`

## Interpretation

The review template has one row per `remediation_id`. Each row defaults to `review_status=needs_review` and preserves the provider, blocker type, blocker text, verification command, and resolution hint.

Supported statuses:

- `needs_review`: still blocking.
- `blocked_external_change`: still blocking; controlled local environment or credential change is needed.
- `adapter_work_required`: still blocking; code-level adapter work is needed.
- `resolved_locally`: non-blocking after local evidence and verification.
- `accepted_out_of_scope`: non-blocking for the current research scope.

Phase 4.9 only creates the template and status dictionary. Applying review rows back into readiness evidence is reserved for a later validation phase.
