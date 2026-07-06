# Round620 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round620-20260707` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 652 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round619 financial reporting timeliness coverage ended at 647 unique symbols and remained blocked.
- Round620 started from clean `main` on a dedicated data-pipeline branch.
- Startup context and Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Preflight source audit confirmed factor work remained blocked at 647 / 1,000 unique symbols.
- Sync audit before provider work had no syncable files and no blockers.
- Single-instance check found no active backfill.
- Shard 41 offset 10 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `301526.SZ`, `300009.SZ`, `002527.SZ`, `000809.SZ`, `002646.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 188 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 652 unique symbols and 138,290 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 41 offset 15 limit 5 previewed as 5 / 5 net-new.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, start shard 41 from offset 15 limit 5 with a fresh financial-root overlap preview first. The next planned symbols are `002187.SZ`, `300839.SZ`, `002828.SZ`, `300554.SZ`, and `300970.SZ`.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 652-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
