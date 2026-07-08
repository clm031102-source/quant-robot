# Round684 Next Steps Checklist

Use this after pulling latest `main`. Round684 is expected to be merged back to `main`; do not pull, merge, or revive old Round675, Round676, Round677, Round678, Round679, Round680, Round681, Round682, Round683, or Round684 topic branches after integration.

## Current Truth

```text
Allowed action: one small data_pipeline backfill only, after starting from merged main.
Latest coverage: 972 / 1,000 unique symbols.
Source gate: blocked by unique_symbol_count_below_minimum.
Shard 57 offset 20 is empty; next usable window is shard 58 offset 0 limit 5.
No factors, no IC, no grids, no promotion, no 2026 final-holdout read.
```

The Round630 ten-round review remains the active review record for this run family. It gives GO for source-only continuation and NO-GO for factor, IC, grid, promotion, sign/window tuning, mixed-window harvesting, and final-holdout work.

## Stop Conditions

- Stop if not on a dedicated Round685 branch before provider work.
- Stop if Quant PM startup gate is not `ready` or blockers are not `[]`.
- Stop if process check returns any active financial statement backfill.
- Stop if fresh preview for shard 58 offset 0 is not exactly 5 / 5 net-new symbols.
- Stop if preview symbols are not `002374.SZ`, `002062.SZ`, `300291.SZ`, `603506.SH`, and `300329.SZ`.
- Stop after post-audit if still below 1,000 symbols; document only, do not run factors.

## Start Commands

```powershell
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/data-pipeline-financial-timeliness-round685-20260708
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round685-20260708
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round685-20260708
```

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Fresh preview command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_overlap_preview.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 58 --symbol-offset 0 --symbol-limit 5 --output-dir data\reports\round685_financial_statement_overlap_preview_shard58_offset0_limit5_financial_roots_20260708
```

Backfill command after all gates pass:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 58 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 3000 --output-dir data\processed\round685_financial_statement_shard58_offset0_limit5_20260708
```

This command writes local data under `data\processed` and reports under `data\reports`. Inspect those outputs, but do not stage or commit them.

## Current State

- Round684 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed factor work remained blocked at 967 / 1,000 unique symbols using `--financial-root data\processed`.
- Shard 57 offset 15 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `600816.SH`, `300616.SZ`, `002035.SZ`, `002182.SZ`, `300201.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 245 processed rows, 11 empty requests, and 28 duplicate rows in the quality report.
- Aggregate source audit improved coverage to 972 unique symbols and 205,911 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 57 offset 20 limit 5 returned 0 symbols, confirming the shard 57 boundary.
- Shard 58 offset 0 limit 5 previewed as 5 / 5 net-new.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 972-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
