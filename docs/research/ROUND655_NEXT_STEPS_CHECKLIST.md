# Round655 Next Steps Checklist

Use this after pulling latest `main`. Round655 is expected to be merged back to `main`; do not pull, merge, or revive old Round653, Round654, or Round655 topic branches after integration.

## Current Truth

```text
Allowed action: one small data_pipeline backfill only, after starting from merged main.
Latest coverage: 827 / 1,000 unique symbols.
Source gate: blocked by unique_symbol_count_below_minimum.
Next window: shard 50 offset 15 limit 5.
No factors, no IC, no grids, no promotion, no 2026 final-holdout read.
```

The Round630 ten-round review remains the active review record for this run family. It gives GO for source-only continuation and NO-GO for factor, IC, grid, promotion, sign/window tuning, mixed-window harvesting, and final-holdout work.

## Stop Conditions

- Stop if not on a dedicated Round656 branch before provider work.
- Stop if Quant PM startup gate is not `ready` or blockers are not `[]`.
- Stop if process check returns any active financial statement backfill.
- Stop if fresh preview for shard 50 offset 15 is not exactly 5 / 5 net-new symbols.
- Stop if preview symbols are not `300142.SZ`, `300099.SZ`, `000922.SZ`, `600702.SH`, and `002419.SZ`.
- Stop after post-audit if still below 1,000 symbols; document only, do not run factors.

## Start Commands

```powershell
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/data-pipeline-financial-timeliness-round656-20260708
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round656-20260708
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round656-20260708
```

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Fresh preview command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_overlap_preview.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 50 --symbol-offset 15 --symbol-limit 5 --output-dir data\reports\round656_financial_statement_overlap_preview_shard50_offset15_limit5_financial_roots_20260708
```

Backfill command after all gates pass:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 50 --symbol-offset 15 --symbol-limit 5 --max-endpoint-requests 3000 --output-dir data\processed\round656_financial_statement_shard50_offset15_limit5_20260708
```

This command writes local data under `data\processed` and reports under `data\reports`. Inspect those outputs, but do not stage or commit them.

## Current State

- Round655 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed factor work remained blocked at 822 / 1,000 unique symbols.
- Shard 50 offset 10 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `001896.SZ`, `600395.SH`, `688186.SH`, `000967.SZ`, `600876.SH`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 208 processed rows, 38 empty requests, and 0 duplicate rows in the quality report.
- Aggregate source audit improved coverage to 827 unique symbols and 174,988 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 50 offset 15 limit 5 previewed as 5 / 5 net-new.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 827-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
