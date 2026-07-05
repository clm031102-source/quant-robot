# Round554 Next Steps Checklist

Use this page after syncing `main`.

## Current State

- `main` includes the former `codex/factor-batch-cn-stock-profit-mining-20260704` branch.
- Latest integration merge commit: `3a8fb18c`.
- Remote topic branches: none.
- Local topic branches: none.
- Project completion gate: `complete`.
- `factor_mining_allowed=true`.

## Start The Next Factor Task

Create a new task branch from latest `main`, for example:

```powershell
git checkout main
git pull --ff-only origin main
git checkout -b codex/factor-batch-cn-stock-round555-20260705
```

Then run the required startup gates:

```powershell
python scripts\start_task_context.py --machine office_desktop --task factor_batch
python scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-round555-20260705
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-round555-20260705 --commits-allowed --pushes-allowed --confirm-start
python scripts\run_cn_stock_data_manifest.py
```

Only begin factor generation after those gates clear.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Treating paper or research evidence as live-trading approval.
- Final-holdout reads unless the relevant promotion gate explicitly requires and allows them.
- Committing generated `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
