# Round614 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round614-20260706` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 622 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round613 financial reporting timeliness coverage ended at 617 unique symbols and remained blocked.
- Round614 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Single-instance check found no active backfill.
- Shard 40 offset 0 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `000969.SZ`, `002158.SZ`, `002228.SZ`, `000928.SZ`, `002343.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 622 unique symbols and 132,258 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 40 offset 5 limit 5 previewed as 5 / 5 net-new.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. Before Round615 provider work, run the two-reviewer checkpoint because the last checkpoint was Round605.
3. If the checkpoint clears continuing financial reporting timeliness, start shard 40 from offset 5 limit 5 with a fresh financial-root overlap preview first. The next planned symbols are `300917.SZ`, `603129.SH`, `002607.SZ`, `002015.SZ`, and `002627.SZ`.
4. Keep provider-consuming batches small enough to audit and resume cleanly.
5. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 622-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
