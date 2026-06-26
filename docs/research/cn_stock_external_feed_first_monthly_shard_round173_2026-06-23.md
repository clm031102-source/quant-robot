# CN Stock External Feed First Monthly Shard Round173

Date: 2026-06-23

Scope: CN stock external macro, northbound, margin, index-state, and macro-rate feeds.

## Trigger

Round172 produced a 132-shard monthly backfill plan for 2015-01-01 through 2025-12-31. The first executable shard was run on the newest complete historical month, 2025-12-01 through 2025-12-31, before allowing broader backfill.

## Engineering Change

Round173 added observable progress logging to `scripts/run_tushare_external_feed_ingest.py`:

- `--progress-jsonl` writes one JSONL event per endpoint/date start and completion.
- Core ingestion now supports `progress_callback`.
- This prevents long Tushare backfills from becoming opaque when an endpoint stalls.

## Shard Command

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-12-01 --end-date 2025-12-31 --output-dir data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --report-copy-dir data\reports\round172_external_feed_long_cycle_backfill_shard_reports_20260623\shard_202512 --execute-write-processed --progress-jsonl data\reports\round173_external_feed_first_monthly_shard_202512_20260623\progress.jsonl
```

## Ingestion Result

- Progress events: 190
- Feed summary: 4 pass, 1 warn, 0 fail
- `external_margin_detail`: 98,278 rows, 2025-12-01 to 2025-12-31, 0 lag violations, 0 missing `available_date`
- `external_hsgt_flow`: 21 rows, 2025-12-01 to 2025-12-31, 0 lag violations, 0 missing `available_date`
- `external_index_state`: 23 rows, 2025-12-01 to 2025-12-31, 0 lag violations, 0 missing `available_date`
- `external_macro_rates`: 23 rows, warn because LPR was missing/rate-limited; SHIBOR fields were available
- `external_hk_hold`: 3,325 CN-stock rows after filtering, only 2025-12-31 retained under the current endpoint response shape

## Join Smoke Result

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round173_external_feed_first_monthly_shard_join_smoke_20260623
```

Result:

- Seed count: 6
- Joined rows: 203,344
- `available_date` violations: 0
- Raw same-day/future date violations: 0
- Pass: 0
- Warn: 0
- Fail: 0
- Insufficient history: 6

## Decision

This is usable engineering evidence, not profitability evidence. The first shard proves the long-cycle external-feed backfill can run with progress logs, write processed partitions, and join pre-registered seeds without PIT violations. It does not justify IC claims, portfolio grids, or promotion.

## Next Direction

Round174 should continue monthly backfill with the same observable shard process, while auditing:

- LPR missing/rate-limit behavior before using LPR factors.
- HK hold endpoint coverage, because CN-stock rows currently appear only on 2025-12-31 for this shard.
- Join-smoke history readiness after enough monthly shards accumulate.
- No external-feed portfolio grid until long-cycle coverage and walk-forward evidence exist.
