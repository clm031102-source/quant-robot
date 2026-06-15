# Phase 4.16 Data Gap Evidence Pack

Phase 4.16 adds a local-only evidence step before changing ETF data-gap resolution statuses.

It does not mark any gap as resolved. Instead, it reads the current gap rows and local TradingView raw CSV files, then records:

- whether the target raw CSV contains the missing date;
- how many peer ETF raw CSV files traded on that same date;
- the target asset's previous and next local raw dates;
- a review hint for manual suspension/no-trade or external backfill decisions.

Run it with:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_evidence.py --output-dir data\reports\data_gap_evidence
```

Outputs:

- `data_gap_evidence_pack.json`
- `data_gap_evidence_pack.md`
- `data_gap_evidence_rows.csv`
- `data_gap_evidence_action_queue.csv`

The pack is research-only. It does not connect to a broker, read accounts, place orders, or cross a live API boundary.
