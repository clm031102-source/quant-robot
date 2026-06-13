# Phase 4.2 Data Gap Resolution Ledger

Phase 4.2 turns exact missing ETF dates into a local resolution ledger.

It remains research-only. It does not call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Ledger builder in `quant_robot.ops.data_gap_resolution`.
- CLI artifact generation through `scripts/run_data_gap_resolution.py`.
- Core-check integration immediately after the data-quality audit.
- Stable `gap_id` values for every missing asset/date row.
- Optional local resolution CSV support for review notes.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Optional local resolution notes:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --resolution-file data\reports\data_gap_resolution\gap_resolutions.csv --output-dir data\reports\data_gap_resolution
```

Resolution CSV columns:

- `gap_id`
- `resolution_status`
- `evidence_note`
- `reviewed_by`
- `reviewed_at`

Supported `resolution_status` values:

- `needs_review`
- `backfill_required`
- `accepted_non_trading_day`
- `accepted_suspension_or_no_trade`
- `resolved_with_backfill`

Output files:

- `data_gap_resolution_ledger.json`
- `data_gap_resolution_ledger.md`
- `data_gap_resolution_rows.csv`
- `data_gap_resolution_action_queue.csv`
- `gap_resolutions_template.csv`
- `data_gap_resolution_status_options.csv`
- `data_gap_resolution_validation.csv`

## Interpretation

The default status for every missing date is `needs_review`, which blocks future API-boundary planning. A row stops blocking only when a local resolution file marks it as an accepted non-trading day, accepted no-trade/suspension case, or resolved backfill.

The current local state is expected to remain blocked until all six CN ETF missing-date rows have explicit local evidence.

Phase 4.4 adds a fillable template generated from the same ledger so local evidence can be recorded without hand-copying gap IDs.

Phase 4.5 adds validation output so unknown gap IDs, invalid statuses, and duplicate resolution rows are reported instead of being silently applied.
