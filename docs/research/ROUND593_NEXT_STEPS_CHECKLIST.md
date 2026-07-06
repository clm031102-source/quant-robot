# Round593 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round593-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 524 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round592 financial reporting timeliness coverage ended at 521 unique symbols and remained blocked.
- Round593 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Single-instance check found no active backfill.
- Shard 35 offset 0 limit 5 was not used for provider work because it contained one already-covered symbol, `000090.SZ`.
- Shard 35 offset 0 limit 3 was confirmed as 3 / 3 net-new within financial statement roots.
- Backfilled symbols: `000962.SZ`, `002097.SZ`, `002191.SZ`.
- Backfill passed with blockers `[]`, 396 endpoint requests, 132 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 524 unique symbols and 112,119 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, continue shard 35 from offset 4 with a financial-root overlap preview first.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 524-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
