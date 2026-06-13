# Phase 3.5 Manual Review Gate Rehearsal

Phase 3.5 rehearses the manual review gate as a local dry run.

It is still research-only. It does not connect to a broker, read accounts, place orders, enable live trading, or approve live review.

## What It Adds

- Manual review rehearsal builder in `quant_robot.ops.manual_review_rehearsal`.
- CLI artifact generation through `scripts/run_manual_review_rehearsal.py`.
- Core-check integration after Promotion Review.
- Evidence Refresh now recommends a dry-run manual gate rehearsal when the manual review gate is blocked.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_manual_review_rehearsal.py --output-dir data\reports\manual_review_rehearsal
```

Output files:

- `manual_review_rehearsal.json`
- `manual_review_rehearsal.md`
- `manual_review_requirements.csv`

## Interpretation

The rehearsal checks:

- research boundary text still says no broker, no account reads, and no order placement;
- manual live review is explicitly enabled;
- data quality blockers are clear;
- providers and Parquet are ready;
- paper observation evidence exists;
- duplicate registry review is visible;
- the dry run itself would not cross a live boundary.

The current local state remains blocked because data quality still has missing date rows, provider readiness is not clean, and manual live review is not enabled. The dry run explicitly records `broker_connection=disabled`, `account_reads=disabled`, and `order_placement=disabled`.

## Current Role In The Roadmap

Phase 3.5 is the final pre-API rehearsal stage in this roadmap. It does not make the system tradable. It makes the remaining blockers concrete before any later API-boundary planning starts.
