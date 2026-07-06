# Round594 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round594-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 528 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round593 financial reporting timeliness coverage ended at 524 unique symbols and remained blocked.
- Round594 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Single-instance check found no active backfill.
- Shard 35 offset 4 limit 4 was confirmed as 4 / 4 net-new within financial statement roots.
- Backfilled symbols: `300027.SZ`, `002968.SZ`, `603766.SH`, `002575.SZ`.
- Backfill passed with blockers `[]`, 471 endpoint requests, 157 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 528 unique symbols and 112,899 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. Before provider work in Round595, run the scheduled two-reviewer checkpoint, then continue shard 35 from offset 9 with a financial-root overlap preview first.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 528-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
