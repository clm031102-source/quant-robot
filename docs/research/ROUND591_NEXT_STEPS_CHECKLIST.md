# Round591 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round591-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 520 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round590 financial reporting timeliness coverage ended at 515 unique symbols and remained blocked.
- Round591 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Single-instance check found no active backfill.
- Shard 34 offset 14 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `600132.SH`, `600736.SH`, `002324.SZ`, `002423.SZ`, `002631.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 221 processed rows, and 1 duplicate row in the quality report.
- Aggregate source audit improved coverage to 520 unique symbols and 111,232 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, finish shard 34 from offset 19 limit 1 with a financial-root overlap preview first.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 520-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
