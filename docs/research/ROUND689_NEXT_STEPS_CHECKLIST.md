# Round689 Next Steps Checklist

Use this after pulling latest `main`. Round689 is expected to be merged back to `main`; do not pull, merge, or revive old Round675, Round676, Round677, Round678, Round679, Round680, Round681, Round682, Round683, Round684, Round685, Round686, Round687, Round688, or Round689 topic branches after integration.

## Current Truth

```text
Allowed action: one small data_pipeline backfill only, after starting from merged main.
Latest coverage: 997 / 1,000 unique symbols.
Source gate: blocked by unique_symbol_count_below_minimum.
Next window: shard 59 offset 5 limit 5.
No factors, no IC, no grids, no promotion, no 2026 final-holdout read.
```

The Round630 ten-round review remains the active review record for this run family. It gives GO for source-only continuation and NO-GO for factor, IC, grid, promotion, sign/window tuning, mixed-window harvesting, and final-holdout work until the source gate clears in a fresh post-backfill audit.

## Stop Conditions

- Stop if not on a dedicated Round690 branch before provider work.
- Stop if Quant PM startup gate is not `ready` or blockers are not `[]`.
- Stop if process check returns any active financial statement backfill.
- Stop if fresh preview for shard 59 offset 5 is not exactly 5 / 5 net-new symbols.
- Stop if preview symbols are not `002550.SZ`, `300124.SZ`, `002056.SZ`, `600199.SH`, and `600655.SH`.
- After post-audit, run factors only if the source gate clears in that fresh audit; otherwise document only.

## Start Commands

```powershell
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/data-pipeline-financial-timeliness-round690-20260708
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round690-20260708
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round690-20260708
```

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Fresh preview command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_overlap_preview.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 59 --symbol-offset 5 --symbol-limit 5 --output-dir data\reports\round690_financial_statement_overlap_preview_shard59_offset5_limit5_financial_roots_20260708
```

Backfill command after all gates pass:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 59 --symbol-offset 5 --symbol-limit 5 --max-endpoint-requests 3000 --output-dir data\processed\round690_financial_statement_shard59_offset5_limit5_20260708
```

This command writes local data under `data\processed` and reports under `data\reports`. Inspect those outputs, but do not stage or commit them.

## Current State

- Round689 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed factor work remained blocked at 992 / 1,000 unique symbols using `--financial-root data\processed`.
- Shard 59 offset 0 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `601018.SH`, `000875.SZ`, `600348.SH`, `002210.SZ`, `600293.SH`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, 0 empty requests, and 0 duplicate rows in the quality report.
- Aggregate source audit improved coverage to 997 unique symbols and 211,289 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 59 offset 5 limit 5 previewed as 5 / 5 net-new.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 997-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning unless a fresh post-backfill audit clears the source gate.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
