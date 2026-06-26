# CN Stock Financial PIT Signal-Date Filter Round202

Date: 2026-06-23

## Objective

Round202 turns the Round200 financial PIT timing audit findings into a reusable filtered financial input root.

Round200 proved that raw `fina_indicator` shard1 full100 data had clean PIT dates but still contained stale/unmapped financial signal rows. Round202 removes those rows and emits explicit `available_date`, `signal_date`, and `signal_lag_calendar_days` columns.

This round does not mine or promote factors.

## Implemented Tool

Added:

- `src/quant_robot/ops/financial_pit_signal_date_filter.py`
- `scripts/run_financial_pit_signal_date_filter.py`
- `tests/unit/test_financial_pit_signal_date_filter.py`
- `tests/unit/test_financial_pit_signal_date_filter_cli.py`

The filter:

- maps each financial row to the first trade date strictly after `ann_date`;
- drops rows with no later trade date;
- drops rows whose announcement-to-signal lag is above 30 calendar days;
- preserves `ann_date` and `end_date`;
- adds `available_date`, `signal_date`, and `signal_lag_calendar_days`;
- keeps exact duplicate financial keys as hard blockers rather than silently deduping.

## Real Filter Run

Command:

```powershell
python scripts\run_financial_pit_signal_date_filter.py --financial-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-root data\processed\round202_financial_pit_signal_filtered_20260623 --max-signal-lag-calendar-days 30
```

Result:

- Input rows: 4,328
- Filtered rows: 4,211
- Dropped stale signal-lag rows: 116
- Dropped unmapped signal rows: 1
- Missing PIT date rows: 0
- `ann_date < end_date` rows: 0
- Exact duplicate key rows: 0
- Output root: `data/processed/round202_financial_pit_signal_filtered_20260623`

## Post-Filter Timing Audit

Command:

```powershell
python scripts\run_financial_pit_timing_audit.py --financial-root data\processed\round202_financial_pit_signal_filtered_20260623 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round202_financial_pit_timing_audit_after_signal_filter_20260623 --max-timing-rows 6000 --max-signal-lag-calendar-days 30
```

Result:

- Passes: true
- Financial rows: 4,211
- Financial assets: 100
- `available_date` present: true
- Missing PIT rows: 0
- `ann_date < end_date` rows: 0
- Exact duplicate key rows: 0
- Signal mapped rows: 4,211
- Signal unmapped rows: 0
- Stale signal-lag rows: 0
- Signal alignment violations: 0
- Max signal lag: 30 calendar days
- Revision groups observed: 0

## Decision

Use `data/processed/round202_financial_pit_signal_filtered_20260623` for future financial/profitability factor matrices instead of the raw Round95 root.

This closes the announcement-date/report-period timing blockers for this shard, but revised-statement handling remains partial because the real sample has no observed revision groups. The project must still preserve distinct `ann_date` rows and reject duplicate financial keys in any future refresh.

## Config Updates

Updated:

- `configs/factor_mining_quality_gate_cn_stock.json`
- `configs/factor_mining_startup_cn_stock.json`

Quality gate changes:

- `financial_statement_ann_date_lag`: implemented
- `report_release_lag_not_period_end`: implemented
- `financial_revision_announcement_handling`: still partial

## Next Action

Before mining profitability factors, update factor-matrix builders to read the Round202 filtered root and emit the same PIT fields into every factor row:

- `report_period` / `end_date`
- `ann_date`
- `available_date`
- `signal_date`
- `signal_lag_calendar_days`

Any future financial refresh must rerun this filter and timing audit before IC or portfolio work.
