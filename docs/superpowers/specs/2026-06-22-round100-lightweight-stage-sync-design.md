# Round100 Lightweight Stage Sync Design - 2026-06-22

## Objective

Package the Round91-99 CN stock factor-validation work into a lightweight GitHub-syncable checkpoint.

Round100 is not a new factor-mining round. It is the ten-round cadence checkpoint required by the project goal: summarize results, verify safety, sync code/config/tests/docs, and leave large data outputs out of Git.

## Scope

Syncable:

- Source code
- CLI scripts
- Unit tests
- Config updates
- Lightweight research reports
- Superpowers specs and plans

Not syncable:

- `data/raw/`
- `data/processed/`
- `data/reports/`
- Parquet/CSV market data
- Tushare token or credentials
- Broker/account/order/live trading artifacts

## Evidence To Preserve

- Round91-95: Tushare `fina_indicator` PIT data path and shard backfill.
- Round96: 14 profitability-quality candidates pre-registered.
- Round97: factor matrix and label alignment smoke passed.
- Round98: controlled IC screen found zero multiple-testing leads.
- Round99: profitability-quality family hibernated and next research family selected.

## Next Research Direction

After sync:

```text
capacity_safe_price_volume_lowvol_reversal_composite_preregistration
```

This must start from pre-registration and IC/quantile/turnover screening, not from portfolio-grid parameter tuning.
