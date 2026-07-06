# Round621 Next Steps Checklist

Use this after pulling latest `main`. Round621 is expected to be merged back to `main`; do not pull, merge, or revive the old Round620 or Round621 topic branches after integration.

## Current Truth

```text
Allowed action: one small data_pipeline backfill only.
Latest coverage: 657 / 1,000 unique symbols.
Source gate: blocked by unique_symbol_count_below_minimum.
Next window: shard 42 offset 0 limit 5.
No factors, no IC, no grids, no promotion, no 2026 final-holdout read.
```

## Stop Conditions

- Stop if not on a dedicated Round622 branch before provider work.
- Stop if Quant PM startup gate is not `ready` or blockers are not `[]`.
- Stop if process check returns any active financial statement backfill.
- Stop if fresh preview is not exactly 5 / 5 net-new symbols.
- Stop if preview symbols are not `603885.SH`, `601579.SH`, `002293.SZ`, `600545.SH`, and `300051.SZ`.
- Stop after post-audit if still below 1,000 symbols; document only, do not run factors.

## Start Commands

```powershell
git status --short --branch
git pull --ff-only origin main
git switch -c codex/data-pipeline-financial-timeliness-round622-20260707
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round622-20260707
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task data_pipeline --branch codex/data-pipeline-financial-timeliness-round622-20260707
```

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Fresh preview command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_overlap_preview.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 42 --symbol-offset 0 --symbol-limit 5 --output-dir data\reports\round622_financial_statement_overlap_preview_shard42_offset0_limit5_financial_roots_20260707
```

Backfill command after all gates pass:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 42 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 3000 --output-dir data\processed\round622_financial_statement_shard42_offset0_limit5_20260707
```

This command writes local data under `data\processed` and reports under `data\reports`. Inspect those outputs, but do not stage or commit them.

## Current State

- Round620 financial reporting timeliness coverage ended at 652 unique symbols and remained blocked.
- Round621 completed the required ten-round review checkpoint after Round620.
- Quant PM review: `GO` for source-only backfill, `NO-GO` for factor work.
- Ordinary-user review: make Round621/Round622 docs explicit that old branches are already integrated and provider work must start from a fresh task branch.
- Round621 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed factor work remained blocked at 652 / 1,000 unique symbols.
- Shard 41 offset 15 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `002187.SZ`, `300839.SZ`, `002828.SZ`, `300554.SZ`, `300970.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 199 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 657 unique symbols and 139,280 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 41 offset 20 limit 5 previewed as empty, so shard 41 is exhausted.
- Shard 42 offset 0 limit 5 previewed as 5 / 5 net-new.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 657-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
