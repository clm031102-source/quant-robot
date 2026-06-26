# CN Stock Financial PIT Timing Audit Round200

Date: 2026-06-23

## Objective

Round200 closes the next pre-mining control gap after the Round199 tradeability fix: financial point-in-time timing and revision safety.

This round does not mine, backtest, or promote any factor. It adds a reusable audit that must run before financial/profitability factor generation.

## Implemented Tool

Added:

- `src/quant_robot/ops/financial_pit_timing_audit.py`
- `scripts/run_financial_pit_timing_audit.py`
- `tests/unit/test_financial_pit_timing_audit.py`
- `tests/unit/test_financial_pit_timing_audit_cli.py`

The audit enforces:

- required financial keys: `asset_id`, `symbol`, `market`, `source`, `ann_date`, `end_date`;
- no missing `ann_date` or `end_date`;
- no `ann_date < end_date`;
- exact duplicate keys `asset_id/end_date/ann_date/source` are hard blockers;
- same `asset_id/end_date` with multiple distinct `ann_date` values is treated as a revision-aware group, not collapsed;
- financial rows map to the first trade date strictly after `ann_date`;
- same-day announcement trading is blocked;
- missing signal dates are blocked;
- stale announcement-to-signal mappings above 30 calendar days are blocked.

## Real Data Audit

Command:

```powershell
python scripts\run_financial_pit_timing_audit.py --financial-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round200_financial_pit_timing_audit_20260623 --allow-not-ready --max-timing-rows 6000 --max-signal-lag-calendar-days 30
```

Output:

- `data/reports/round200_financial_pit_timing_audit_20260623/financial_pit_timing_audit.json`
- `data/reports/round200_financial_pit_timing_audit_20260623/financial_pit_timing_audit.md`
- `data/reports/round200_financial_pit_timing_audit_20260623/financial_pit_timing_audit_timing_rows.csv`

## Key Numbers

- Financial rows: 4,328
- Financial assets: 100
- Bar rows used for those assets: 266,894
- `ann_date` range: 2015-04-15 to 2026-04-30
- Report period range: 2015-03-31 to 2025-12-31
- Missing PIT rows: 0
- `ann_date < end_date` rows: 0
- Exact duplicate key rows: 0
- Observed revision groups: 0
- Signal alignment violations: 0
- Signal mapped rows: 4,327
- Signal unmapped rows: 1
- Stale signal-lag rows over 30 calendar days: 116
- Max announcement-to-signal lag: 1,474 calendar days

Largest stale-lag concentration:

- `CN_XSHE_000029`: 16 stale rows, max lag 1,474 days.
- `CN_XSHE_000155`: 8 stale rows, max lag 598 days.
- Stale rows span 43 assets.

## Decision

The financial timing control improved, but it is not ready for direct financial factor mining.

The shard has clean PIT dates and no duplicate keys, but stale and unmapped signal-date mappings mean some historical financial observations would become signals years after the announcement simply because bars start late. That is not lookahead, but it is economically invalid stale information and can distort IC or portfolio tests.

Direct profitability factor generation remains blocked until stale/unmapped financial signal rows are filtered or repaired and the audit passes.

## Config Updates

Updated:

- `configs/factor_mining_quality_gate_cn_stock.json`
- `configs/factor_mining_startup_cn_stock.json`
- `src/quant_robot/ops/factor_mining_startup.py`

The startup protocol now requires:

- `financial_pit_timing_audit_before_financial_factor_generation`
- `financial_signal_lag_stale_threshold_required`
- `financial_exact_duplicate_key_blocker_required`
- `financial_revision_distinct_ann_date_preservation_required`
- `financial_pit_timing_audit_confirmed`
- `financial_stale_or_unmapped_signal_rows_blocked`
- `financial_exact_duplicate_keys_blocked`
- `financial_same_day_announcement_trading_rejected`

## Next Action

Build a filtered financial factor input or matrix path that excludes:

- rows with missing strict `signal_date`;
- rows with `signal_lag_calendar_days > 30`;
- exact duplicate financial keys;
- any future observed revisions that collapse distinct `ann_date` rows.

Then rerun this audit and only resume profitability-factor IC screening if it passes.
