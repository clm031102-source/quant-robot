# Phase 3.2 Provider Readiness Evidence

Phase 3.2 turns optional data-provider readiness into durable local evidence.

It is still research-only. It does not connect to providers, brokers, accounts, or order systems.

## What It Adds

- Provider evidence builder in `quant_robot.ops.provider_evidence`.
- CLI artifact generation through `scripts/run_provider_evidence.py`.
- Core-check integration after provider status.
- Evidence Refresh now recommends a provider evidence pack before generic readiness checks.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_evidence.py --output-dir data\reports\provider_evidence
```

To reuse a saved provider-status payload:

```powershell
$env:PYTHONPATH='src'
python scripts\show_provider_status.py --output data\reports\provider_status\provider_status.json
python scripts\run_provider_evidence.py --provider-status data\reports\provider_status\provider_status.json --output-dir data\reports\provider_evidence
```

Output files:

- `provider_evidence_pack.json`
- `provider_evidence_pack.md`
- `provider_market_matrix.csv`
- `provider_readiness.csv`

## Interpretation

Provider status now distinguishes:

- `ready`: package, token, and implementation are all available.
- `missing_dependency`: optional package is not installed.
- `missing_token`: required token is not set.
- `missing_dependency_and_token`: both dependency and token are missing.
- `planned_adapter`: adapter work is planned but not implemented.
- `blocked`: provider is not ready for another local reason.

The market matrix labels provider/market coverage as:

- `implemented_ready`: adapter exists and the provider is locally ready.
- `implemented_blocked`: adapter exists but local package/token readiness blocks use.
- `planned`: coverage is planned but not implemented.

## Why It Matters

Promotion review and Evidence Refresh previously saw provider readiness as one coarse blocker. This phase makes the blocker actionable: Tushare token/package gaps, AKShare planned-adapter status, yfinance/ccxt readiness, and Parquet storage readiness are visible in one evidence pack.

After dependency or token changes, rerun:

```powershell
$env:PYTHONPATH='src'
python scripts\show_provider_status.py --output data\reports\provider_status\provider_status.json
python scripts\run_provider_evidence.py --provider-status data\reports\provider_status\provider_status.json --output-dir data\reports\provider_evidence
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
python scripts\run_evidence_refresh.py --output-dir data\reports\evidence_refresh
```
