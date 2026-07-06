# Round585 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round585-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 492 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round584 financial reporting timeliness coverage ended at 487 unique symbols and remained blocked.
- Round585 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- The scheduled two-reviewer checkpoint returned GO for a small audited data-pipeline backfill only.
- Single-instance check found no active backfill.
- Shard 33 offset 5 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `000895.SZ`, `002548.SZ`, `001337.SZ`, `002197.SZ`, `600421.SH`.
- Backfill passed with blockers `[]`, 564 endpoint requests, 188 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 492 unique symbols and 105,325 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, continue shard 33 from offset 10 with a financial-root overlap preview first.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 492-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
