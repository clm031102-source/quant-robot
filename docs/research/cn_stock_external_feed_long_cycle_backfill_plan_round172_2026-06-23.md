# CN Stock External Feed Long-Cycle Backfill Plan Round172

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round171 proved that external feed factor-matrix joins can respect `available_date <= signal_date`, including a secondary feed for `north_money`. It also proved the current sample is too short: all six seeds were `insufficient_history`.

An attempted 2025Q4 pilot process produced no stdout/stderr progress for several minutes and was stopped to avoid an unbounded API wait. The response was to build a shard plan instead of pushing a large date range through one opaque process.

## Engineering Change

Added a reusable backfill planner:

- `src/quant_robot/ops/external_feed_backfill_plan.py`
- `scripts/run_external_feed_backfill_plan.py`
- `tests/unit/test_external_feed_backfill_plan.py`
- `tests/unit/test_external_feed_backfill_plan_cli.py`

Also added `--report-copy-dir` to `scripts/run_tushare_external_feed_ingest.py` so every shard can write into one common processed root while preserving a per-shard report copy.

## Generated Plan

Command:

```powershell
python scripts\run_external_feed_backfill_plan.py --start-date 2015-01-01 --end-date 2025-12-31 --output-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-root data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623 --output-dir data\reports\round172_external_feed_long_cycle_backfill_plan_20260623 --shard-months 1 --max-estimated-business-days-per-shard 25
```

Result:

- Status: ready
- Monthly shards: 132
- Estimated business days: 2,870
- Estimated endpoint calls: 11,745
- Over-budget shards: 0

## Execution Policy

Run shards one at a time. After each shard:

- Inspect `external_feed_ingestion_report.json`.
- Confirm no duplicate keys, lag violations, or missing `available_date`.
- Re-run `external_feed_factor_matrix_join_smoke`.
- Confirm 0 `available_date` violations.
- Confirm 0 raw same-day/future date violations.
- Keep `data/raw`, `data/processed`, `data/reports`, logs, and cache files out of Git.

## Blocked Uses

- Do not run portfolio grids from a short join smoke.
- Do not claim IC or profitability from ingestion coverage.
- Do not use LPR factors until LPR non-missing coverage is proven.
- Do not promote external-feed factors before long-cycle join smoke, neutralization, redundancy, regime, cost/capacity, and walk-forward gates.

## Next Direction

Round173 should execute one small monthly shard first, preferably the newest complete historical month, then run the join smoke on the common processed root. If it completes cleanly and produces observable per-shard reports, continue monthly backfill.

