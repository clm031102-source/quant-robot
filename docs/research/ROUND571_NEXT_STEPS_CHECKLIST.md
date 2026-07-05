# Round571 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round571-20260705` or after this branch is merged to `main`.

## Current State

- Round570 financial reporting timeliness coverage ended at 417 unique symbols and remained blocked.
- Round571 started from clean `main` on a dedicated data-pipeline branch.
- Quant PM startup gate passed for `office_desktop` / `data_pipeline`.
- Shard 25 offset 15 limit 5 was confirmed as 5 / 5 net-new within financial statement roots.
- Backfilled symbols: `600769.SH`, `000935.SZ`, `600798.SH`, `000868.SZ`, `600822.SH`.
- Backfill passed with blockers `[]`, 660 endpoint requests, 220 processed rows, and no pre-listing skips.
- Aggregate source audit improved coverage to 422 unique symbols and 90,233 rows.
- Shard 25 is complete in the local financial statement roots.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, move to the next high net-new shard, starting with a financial-root overlap preview.
3. Keep provider-consuming batches small enough to audit and resume cleanly.
4. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols and enough end-year coverage.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 422-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
