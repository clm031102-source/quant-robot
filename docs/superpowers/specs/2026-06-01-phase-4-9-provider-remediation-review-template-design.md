# Phase 4.9 Provider Remediation Review Template Design

## Purpose

Phase 4.9 turns provider-remediation rows into a fillable local review template. The goal is to let an operator record controlled local evidence for each dependency, credential, adapter, and storage blocker without editing the generated remediation matrix directly.

## Scope

The feature only writes local CSV artifacts from existing provider-remediation evidence. It does not install packages, set tokens, validate secrets, call providers, connect to brokers, read accounts, place orders, or enable live trading.

Out of scope:

- Automatic package installation.
- Automatic token handling.
- Provider downloads or network calls.
- Applying review rows back into readiness state.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.ops.provider_remediation` gains two pure helpers:

- `build_review_template_rows(matrix)` returns one fillable row per remediation item.
- `remediation_status_options()` returns supported review statuses and whether each status still blocks provider readiness.

`write_provider_remediation_matrix()` writes two additional CSV files:

- `provider_remediation_review_template.csv`
- `provider_remediation_status_options.csv`

The template preserves each `remediation_id`, provider, blocker type, blocker text, resolution hint, and verification command. It adds blank review fields plus default `review_status=needs_review`.

Supported statuses are:

- `needs_review`
- `blocked_external_change`
- `adapter_work_required`
- `resolved_locally`
- `accepted_out_of_scope`

Only `resolved_locally` and `accepted_out_of_scope` are non-blocking. These statuses are documentation aids in Phase 4.9; they are not applied to readiness calculations until a later validation phase.

## Testing

Use unittest:

- `tests/unit/test_provider_remediation.py`
- `tests/unit/test_provider_remediation_cli.py`

The pure test must prove that template rows preserve remediation IDs and include allowed statuses. The CLI test must prove that both new CSV artifacts are written.

Full verification requires regenerating real provider-remediation artifacts and running `scripts/run_checks.py --execute`.
