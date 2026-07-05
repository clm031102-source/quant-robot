# Round575 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round575-20260705` or after this branch is merged to `main`.

## Operator Start Here

Status: still blocked at 442 / 1,000 unique symbols. No factors, no IC, no grids, no promotion, no 2026 final-holdout read.

Before provider work, check for an active backfill:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_financial_statement_shard_backfill.py*' } | Select-Object ProcessId,ParentProcessId,CommandLine
```

Stop if an existing process is writing to the same output root.

## Current State

- Round574 financial reporting timeliness coverage ended at 437 unique symbols and remained blocked.
- Round575 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Scheduled two-agent review was completed before documenting the round.
- Quant PM reviewer recommended continuing only tiny audited net-new windows and keeping all factor work blocked until the full source gate clears.
- Operator reviewer recommended explicit single-instance process checks and copy-safe status text.
- Shard 29 offset 15 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `002263.SZ`, `000987.SZ`, `002615.SZ`, `000801.SZ`, `000960.SZ`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, and 0 duplicate rows.
- Aggregate source audit improved coverage to 442 unique symbols and 94,574 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, move to the next high net-new shard with a financial-root overlap preview first.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols, 8 end years, `candidate_plan_allowed=true`, `source_gate_cleared=true`, and blockers `[]`.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 442-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
