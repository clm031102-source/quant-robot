# Phase 4.7 Provider Remediation Matrix

Phase 4.7 turns provider-readiness evidence into a local remediation matrix.

It remains research-only. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Remediation builder in `quant_robot.ops.provider_remediation`.
- CLI artifact generation through `scripts/run_provider_remediation.py`.
- Core-check integration immediately after `provider_evidence`.
- One remediation row per dependency, credential, adapter, or Parquet blocker.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Output files:

- `provider_remediation_matrix.json`
- `provider_remediation_matrix.md`
- `provider_remediation_items.csv`
- `provider_remediation_summary.csv`

## Interpretation

Each remediation row includes:

- provider or storage scope;
- blocker type;
- exact blocker text from provider evidence;
- local resolution hint;
- verification command;
- provider-readiness blocking flag.

Dependency and credential rows require a user-controlled environment change before the verification command can turn green. The matrix is a local operations aid, not an automatic installer.
