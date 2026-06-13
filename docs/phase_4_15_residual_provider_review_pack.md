# Phase 4.15 Residual Provider Review Pack

Phase 4.15 turns the provider-remediation rows that remain blocking after rehearsal into a focused local review pack.

It remains research-only. It does not install packages, set tokens, call data providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Residual review builder in `quant_robot.ops.residual_provider_review`.
- CLI artifact generation through `scripts/run_residual_provider_review.py`.
- Core-check integration after `residual_data_gap_review`.
- Residual provider-remediation item CSV for rows still blocking after rehearsal.
- A fillable `residual_provider_review_template.csv` that can be passed back to `scripts/run_provider_remediation.py --review-file`.
- A local action queue for readiness checks, provider status refresh, matrix application, rehearsal refresh, projection refresh, and focus refresh.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_provider_review.py --output-dir data\reports\residual_provider_review
```

Output files:

- `residual_provider_review_pack.json`
- `residual_provider_review_pack.md`
- `residual_provider_remediation_items.csv`
- `residual_provider_review_template.csv`
- `residual_provider_action_queue.csv`
- `residual_provider_status_options.csv`

## Interpretation

This pack is a residual review worksheet. It starts from the provider-remediation rehearsal result, so rows accepted as out of scope by the rehearsal sample do not appear in the residual list.

Use `residual_provider_review_template.csv` to record controlled local evidence for the remaining blocking remediation rows, then apply it with:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --review-file data\reports\residual_provider_review\residual_provider_review_template.csv --output-dir data\reports\provider_remediation
```

The pack preserves the API boundary as blocked while residual provider rows remain.
