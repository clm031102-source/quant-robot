# CN Stock Round216 Fina Indicator Stratified Shard1 Full100 PIT Audit

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock profitability-quality data readiness, not ETF rotation
- Stage: full stratified financial data backfill and PIT timing audit

## Objective

Round216 expanded the Round214 stratified `fina_indicator` plan from Round215 first10 to a full 100-symbol shard. The goal was to test whether the stratified sample is clean enough to restart profitability-quality coverage and IC screening.

This round still does not create or promote any factor.

## Commands

```powershell
python scripts\run_fina_indicator_shard_backfill_smoke.py --shard-plan-json data\reports\fina_indicator_stratified_symbol_shard_plan_round214_20260624\fina_indicator_symbol_shard_plan.json --shard-id 1 --max-symbols 100 --batch-size 20 --max-requests 4400 --output-dir data\processed\round216_fina_indicator_stratified_shard1_full100_20260624 --pit-readiness-output-dir data\reports\round216_tushare_financial_pit_readiness_stratified_shard1_full100_20260624
```

```powershell
python scripts\run_financial_pit_signal_date_filter.py --financial-root data\processed\round216_fina_indicator_stratified_shard1_full100_20260624 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-root data\processed\round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624 --max-signal-lag-calendar-days 30
```

```powershell
python scripts\run_financial_pit_timing_audit.py --financial-root data\processed\round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round216_financial_pit_timing_audit_stratified_shard1_full100_20260624 --max-signal-lag-calendar-days 30
```

## Backfill Result

- Selected symbols: 100
- Periods: 44
- Requests: 4,400
- Processed rows: 4,385
- Empty requests: 15
- Skipped requests: 0
- Assets: 100
- Duplicate rows: 0
- Missing asset_id rows: 0
- PIT readiness: passed
- Report period range: 2015-03-31 to 2025-12-31
- Announcement date range: 2015-04-18 to 2026-04-30

Missing numeric rows:

- Total rows with any missing tracked numeric field: 248
- `grossprofit_margin`: 92
- `roa`: 90
- `roe`: 38
- `or_yoy`: 8
- `netprofit_yoy`: 6
- `ocfps`: 5
- `cfps`: 5
- `netprofit_margin`: 4

## PIT Signal-Date Filter

- Input rows: 4,385
- Filtered rows: 4,277
- Dropped stale signal-lag rows: 106
- Dropped unmapped signal rows: 2
- Missing PIT date rows: 0
- Ann-date-before-report-period rows: 0
- Exact duplicate key rows: 0
- Max signal lag allowed: 30 calendar days
- Filter passes: true

## Timing Audit

- Financial rows: 4,277
- Financial assets: 100
- Signal mapped rows: 4,277
- Signal unmapped rows: 0
- Signal alignment violations: 0
- Stale signal-lag rows: 0
- Max signal lag: 27 calendar days
- Missing ann_date rows: 0
- Missing end_date rows: 0
- Revision groups observed: 0
- Timing audit passes: true

## Interpretation

The stratified full100 financial data path is clean enough to restart profitability-quality coverage and IC screening.

This does not overturn the earlier Round98 negative factor result. It only fixes a sampling concern: the old full100 shard was code-ordered, while this shard is industry/exchange/list-year stratified. The next valid question is whether the same preregistered profitability-quality factor family behaves differently on this more representative PIT-clean sample.

## Decision

- New factors: 0
- Research leads: 0
- Promotion candidates: 0
- Data path: accepted for profitability-quality preregistration and label-aligned IC rerun
- Next action: Round217 rerun profitability-quality preregistration/coverage on `data/processed/round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624`

No portfolio grid, TopN conversion, or promotion is allowed from Round216 alone.
