# Round556 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- `run_tushare_alpha_factory.py` now requires a cleared candidate-plan gate packet for CN processed-bars runs.
- The active preregistered factor-name set must match the factor source's actual executed factor names.
- Missing or mismatched candidate-plan packets fail before bar loading.
- A short real local smoke completed with the Round555 candidate-plan packet: 12 / 12 cases completed, 0 adjusted-significant rows.

## Recommended Next Work

1. Rerun the Round555 daily-basic source-readiness smoke over a longer discovery window with `--candidate-plan-gate-packet`.
2. Add the candidate-plan gate packet path to any alpha-factory runbook examples.
3. Consider writing the accepted candidate-plan packet path into alpha-factory `manifest.json` for easier audit traceability.
4. Keep 2026 final holdout excluded from tuning.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from short smoke evidence.
- Committing generated `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
