# Round605 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round605-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 577 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round604 financial reporting timeliness coverage ended at 573 unique symbols and remained blocked.
- Round605 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Scheduled two-reviewer checkpoint returned GO for small audited data-pipeline work only.
- Shard 37 offset 15 limit 5 preview found 4 / 5 net-new and one existing symbol, `000070.SZ`.
- To avoid duplicate provider work, Round605 split the run into shard 37 offset 15 limit 2 and shard 37 offset 18 limit 2.
- Backfilled symbols: `001256.SZ`, `002689.SZ`, `002511.SZ`, `600258.SH`.
- Both backfills passed with blockers `[]`, 435 total endpoint requests, 145 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 577 unique symbols and 123,127 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, start shard 38 from offset 0 limit 5 with a financial-root overlap preview first. The next planned symbols are `002541.SZ`, `601816.SH`, `002114.SZ`, `300697.SZ`, and `002532.SZ`.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 577-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
