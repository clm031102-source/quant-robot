# Round613 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round613-20260706` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 617 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round612 financial reporting timeliness coverage ended at 612 unique symbols and remained blocked.
- Round613 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Single-instance check found no active backfill.
- Shard 39 offset 15 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `600895.SH`, `002395.SZ`, `002647.SZ`, `300163.SZ`, `000921.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 617 unique symbols and 131,147 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- Shard 39 offset 20 limit 5 has no remaining planned symbols.
- Shard 40 offset 0 limit 5 previewed as 5 / 5 net-new.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, start shard 40 from offset 0 limit 5 with a fresh financial-root overlap preview first. The next planned symbols are `000969.SZ`, `002158.SZ`, `002228.SZ`, `000928.SZ`, and `002343.SZ`.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.
5. Run the next two-reviewer checkpoint at Round615 before continuing beyond that round.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 617-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
