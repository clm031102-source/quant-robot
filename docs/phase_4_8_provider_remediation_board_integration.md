# Phase 4.8 Provider Remediation Board Integration

Phase 4.8 connects the provider remediation matrix to the pre-API readiness board.

It remains research-only. It does not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Default loading of `data/reports/provider_remediation/provider_remediation_matrix.json` in `scripts/run_pre_api_readiness_board.py`.
- Explicit `--provider-remediation` CLI input for local remediation artifacts.
- A `provider_remediation` readiness item on the pre-API board.
- A `provider_remediation_items_open` blocker when remediation items remain.
- A local action queue command for `scripts/run_provider_remediation.py`.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

To pass an explicit remediation artifact:

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --provider-remediation data\reports\provider_remediation\provider_remediation_matrix.json --output-dir data\reports\pre_api_readiness_board
```

Output files:

- `pre_api_readiness_board.json`
- `pre_api_readiness_board.md`
- `pre_api_readiness_items.csv`
- `pre_api_blockers.csv`
- `pre_api_next_actions.csv`

## Interpretation

The board marks `provider_remediation` as `block` when the remediation matrix reports any open remediation rows or `blocks_api_boundary=true`.

The readiness evidence includes remediation, dependency, credential, adapter, and storage counts. The blocker is local-only: it tells the operator to rerun provider remediation evidence after controlled environment changes, not to install packages or touch secrets automatically.
