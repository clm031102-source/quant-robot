# Round567 Next Steps Checklist

Use this after pulling `codex/data-pipeline-financial-timeliness-round567-20260705` or after this branch is merged to `main`.

## Current State

- Round565 HK-hold low-frequency sponsorship is rejected as a research lead source family.
- Round566 financial reporting timeliness source audit was blocked at 394 unique symbols.
- Round567 ran a dedicated data-pipeline backfill for shard 19 net-new symbols.
- Backfilled symbols: `002461.SZ`, `600658.SH`, `002014.SZ`, `002571.SZ`, `000762.SZ`, `000811.SZ`, `000917.SZ`, `000668.SZ`.
- Backfill segments passed with blockers `[]`.
- Aggregate source audit improved coverage to 402 unique symbols and 86,264 rows.
- Candidate plan allowed remains false because `unique_symbol_count_below_minimum` still blocks the gate.
- No factor generation, IC screen, portfolio grid, promotion gate, or 2026 final-holdout read was run.

## Recommended Next Work

1. Merge this documentation branch back to `main` after validation.
2. If continuing financial reporting timeliness, run another overlap preview before any provider calls and spend requests only on net-new symbols.
3. Keep factor preregistration blocked until the aggregate audit clears at least 1,000 unique symbols and enough end-year coverage.
4. If backfill throughput is too slow for this source, rotate to another accessible PIT-safe source mechanism and run a candidate-plan gate before any IC screen.

## Explicitly Do Not Do

- Do not generate financial reporting timeliness factors from the 402-symbol cache.
- Do not run residual IC, portfolio grids, promotion gates, or sign/window tuning for this source yet.
- Do not read the 2026 final holdout.
- Do not commit `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or order data.
- Do not connect to a broker, read live accounts, place orders, or enable automatic live trading.
