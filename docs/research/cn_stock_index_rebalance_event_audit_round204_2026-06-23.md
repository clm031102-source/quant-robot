# CN Stock Index Rebalance Event Audit Round204

- Date: 2026-06-23
- Scope: CN stock event-factor coverage control
- Source endpoint: Tushare `index_weight`
- Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Why

The quality gate still had `index_rebalance_events` as a planned blocker. Index inclusion, exclusion, and large weight changes can contaminate stock-level factor results or become separate event hypotheses. Round204 adds a PIT-safe event audit so future index-event tests do not infer events from future constituent knowledge.

## What Changed

- Added `TushareAdapter.fetch_index_weight(index_code, start_date, end_date)`.
- Added `src/quant_robot/ops/index_rebalance_event_audit.py`.
- Added `scripts/run_index_rebalance_event_audit.py`.
- Added unit and CLI tests for:
  - converting two index-weight snapshots into `added`, `removed`, and `weight_changed` events,
  - strict next-trading-day `available_date`,
  - duplicate snapshot key blocking,
  - report output writing.

## Real Smoke

Command path used a live Tushare adapter without printing the token:

- Index: `000300.SH`
- Window: 2023-01-01 through 2024-12-31
- Calendar window: 2023-01-01 through 2025-01-15
- Weight-change threshold: 0.1

Observed:

- Index-weight rows: 7,000
- Calendar rows: 494
- Snapshot dates: 24
- Event rows: 358
- Added events: 228
- Removed events: 28
- Weight-changed events: 102
- Audit blockers: none

## Policy

- `trade_date` is treated as the index-weight snapshot/event date.
- Event `available_date` is the first open trade date strictly after `trade_date`.
- Same-day event trading is not allowed.
- This is event coverage and contamination-control evidence only, not profitability evidence.

## Quality Gate Update

`index_rebalance_events` is upgraded from planned to implemented as a reusable process-control path. Future index inclusion/exclusion alpha tests must attach `index_rebalance_event_audit.json` and `index_rebalance_events.csv` before any IC, TopN, or portfolio interpretation.
