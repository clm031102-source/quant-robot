# Round568 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round568-20260705` or after this branch is merged to `main`.

## Current State

- Round567 financial reporting timeliness coverage ended at 402 unique symbols and remained blocked.
- Round568 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Shard 25 offset 0 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `603071.SH`, `301345.SZ`, `002348.SZ`, `000862.SZ`, `002033.SZ`.
- Backfill passed with blockers `[]`, 483 endpoint requests, 161 processed rows, and 59 pre-listing skipped symbol-periods.
- Aggregate source audit improved coverage to 407 unique symbols and 87,064 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, keep using financial-root overlap previews and avoid whole-`data\processed` previews for this purpose because non-financial asset coverage can overstate "existing" status.
3. Continue shard 25 from offset 5 if provider quota and time allow; the local scan found the remaining shard 25 symbols were also net-new at the time of Round568.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols and enough end-year coverage.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 407-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
