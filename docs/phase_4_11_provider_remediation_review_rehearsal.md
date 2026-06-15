# Phase 4.11 Provider Remediation Review Rehearsal

Phase 4.11 rehearses provider-remediation review rows without changing real remediation evidence.

It remains research-only. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Rehearsal builder in `quant_robot.ops.provider_remediation_rehearsal`.
- CLI artifact generation through `scripts/run_provider_remediation_rehearsal.py`.
- Core-check integration immediately after `provider_remediation`.
- Sample review rows for providers that are out of the current CN ETF research scope.
- Before/after blocking remediation counts.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation_rehearsal.py --output-dir data\reports\provider_remediation_rehearsal
```

Output files:

- `provider_remediation_rehearsal.json`
- `provider_remediation_rehearsal.md`
- `sample_provider_remediation_reviews.csv`
- `rehearsed_provider_remediation_items.csv`
- `provider_remediation_rehearsal_summary.csv`

## Interpretation

The default rehearsal treats `akshare`, `ccxt`, and `yfinance` as out of current CN ETF scope and generates `accepted_out_of_scope` sample review rows for their remediation items.

The rehearsal deliberately leaves `tushare` and `parquet` blockers untouched because clearing those requires controlled local package, credential, or storage changes. Rehearsal artifacts are examples only; they must not be used as real review evidence without replacing the sample notes.
