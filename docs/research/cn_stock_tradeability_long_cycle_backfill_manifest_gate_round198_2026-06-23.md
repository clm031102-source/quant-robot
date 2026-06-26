# CN Stock Tradeability Long-Cycle Backfill Manifest Gate - Round198

Date: 2026-06-23

## Objective

Round198 fixed the pre-mining direction gate after the CN stock factor workflow exposed a serious false-positive readiness issue: a short official tradeability smoke sample could be mistaken for long-cycle readiness. The goal is not to mine new factors yet. The goal is to make sure future CN stock factor mining cannot proceed until full-window official tradeability coverage is proven.

## Implemented Controls

- Added `scripts/run_tushare_tradeability_backfill_plan.py`.
- Added `src/quant_robot/ops/tushare_tradeability_backfill_plan.py`.
- Added monthly shard planning for long-cycle official tradeability backfill.
- Added explicit `--execute` and `--execute-write-processed` gates.
- Added separate report root and processed root handling for Tushare tradeability ingest.
- Added `metadata/tushare_tradeability_feed_coverage` manifest rows for each executed shard.
- Upgraded `cn_stock_tradeability_data_readiness_audit` so official tradeability feeds require expected-window coverage before direct factor generation.
- Startup protocol now requires an official tradeability coverage manifest check before direct CN stock factor mining.

## Long-Cycle Plan

Plan command:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2026-06-23 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_plan_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_shards_20260623
```

Plan result:

- Status: ready
- Planned shards: 138
- Selected shards: 138
- Estimated business days: 2,994
- Estimated endpoint calls: 6,540
- Executed shards in the plan-only run: 0

## Real Shard Smoke

Smoke command:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-01-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_smoke_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_smoke_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_smoke_shards_20260623 --max-shards 1 --snapshot 2026-06-23 --execute --execute-write-processed
```

Smoke result:

- Executed shards: 1
- Passed shards: 1
- Failed shards: 0
- Estimated endpoint calls: 48
- `tradeability_stk_limit`: 51,951 rows, 2,614 entities, 0 lag violations
- `tradeability_suspension`: 5,386 rows, 453 entities, 0 lag violations
- `tradeability_namechange`: 17 rows, 17 entities, 3 ST-name rows, 0 lag violations
- `stock_basic_status`: L/D status present, 5,855 entities, 331 delist-date rows; P is an optional missing warning in live Tushare data

## Readiness Audit Result

Audit command:

```powershell
python scripts\run_cn_stock_tradeability_data_readiness_audit.py --data-root data\processed\cn_stock_long_history_2015_202306 --data-root data\processed\office_desktop_20260616_combined_research --data-root data\processed\cn_stock_metadata --data-root data\processed\round198_tradeability_long_cycle_official_backfill_smoke_20260623 --output-dir data\reports\round198_tradeability_readiness_after_first_smoke_20260623 --expected-start 2015-01-01 --expected-end 2025-12-31
```

Correct post-fix decision:

- Status: `direct_mining_blocked`
- Direct factor generation allowed: false
- Ready controls: 3
- Blocking controls: 3
- `limit_up_down_filter`: `partial_coverage`
- `suspension_filter`: `partial_coverage`
- `st_flag_filter`: `partial_coverage`

The important result is that the audit no longer treats one month of official feed rows as full 2015-2025 readiness. The coverage manifest proves only 2015-01-01 to 2015-01-31 is covered, so direct factor generation stays blocked.

## Production Backfill Progress

After the control fix, the first production-root batch was executed:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201501_201503_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --execute --execute-write-processed
```

Production-root result:

- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2015-03-31
- `tradeability_stk_limit`: 149,413 rows, 2,662 entities
- `tradeability_suspension`: 15,961 rows, 815 entities
- `tradeability_namechange`: 60 rows, 60 entities

Follow-up audit:

- Status: `direct_mining_blocked`
- Direct factor generation allowed: false
- `limit_feed_expected_window_coverage`: `incomplete`
- `suspension_feed_expected_window_coverage`: `incomplete`
- `namechange_feed_expected_window_coverage`: `incomplete`
- Next direction: `round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration`

## Resume-Safe Backfill Progress

The backfill controller now supports `--skip-covered`, which reads `metadata/tushare_tradeability_feed_coverage` from the processed root and skips already-covered monthly shards. This prevents duplicated Tushare calls and reduces the chance of manually rerunning finished months.

Resume plan smoke:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_plan_skip_covered_201501_201506_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered
```

Resume plan result:

- Planned shards: 6
- Covered shards skipped: 3
- Uncovered shards: 3
- Selected shards: 3
- Executed shards in plan-only run: 0

Second production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201504_201506_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Second production-root result:

- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2015-06-30
- `tradeability_stk_limit`: 317,396 rows, 2,782 entities
- `tradeability_suspension`: 39,858 rows, 1,544 entities
- `tradeability_namechange`: 135 rows, 132 entities

Follow-up audit remains correctly blocked:

- Status: `direct_mining_blocked`
- Direct factor generation allowed: false
- `limit_feed_expected_window_coverage`: `incomplete`
- `suspension_feed_expected_window_coverage`: `incomplete`
- `namechange_feed_expected_window_coverage`: `incomplete`
- Next direction: `round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration`

Third production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201507_201509_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Third production-root result:

- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2015-09-30
- `tradeability_stk_limit`: 495,403 rows, 2,787 entities
- `tradeability_suspension`: 77,019 rows, 2,095 entities
- `tradeability_namechange`: 179 rows, 174 entities

Three-batch review:

- The `--skip-covered` path correctly avoided rerunning the first six covered months.
- The manifest merged interval remains continuous with no gaps from 2015-01-01 to 2015-09-30.
- Direct factor generation remains correctly blocked because the expected 2015-01-01 to 2025-12-31 window is not fully covered.
- Next action stays unchanged: continue monthly official tradeability backfill, then integrate masks only after coverage is complete.

Fourth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2015-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201510_201512_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Fourth production-root result:

- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2015-12-31
- `tradeability_stk_limit`: 665,312 rows, 2,817 entities
- `tradeability_suspension`: 99,056 rows, 2,195 entities
- `tradeability_namechange`: 219 rows, 212 entities

2015 coverage review:

- 12 monthly shards are covered continuously from 2015-01-01 through 2015-12-31.
- No coverage gaps are reported by the readiness audit.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- The correct continuation is to use `--skip-covered` and extend the same production root into 2016 onward.

Fifth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2016-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201601_201603_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Fifth production-root result:

- Covered shards skipped: 12
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2016-03-31
- `tradeability_stk_limit`: 831,520 rows, 2,841 entities
- `tradeability_suspension`: 115,378 rows, 2,287 entities
- `tradeability_namechange`: 283 rows, 255 entities

Follow-up audit remains correctly blocked:

- Status: `direct_mining_blocked`
- Direct factor generation allowed: false
- `limit_feed_expected_window_coverage`: `incomplete`
- `suspension_feed_expected_window_coverage`: `incomplete`
- `namechange_feed_expected_window_coverage`: `incomplete`
- Manifest coverage is continuous with no gaps, but only through 2016-03-31.
- Next direction remains `round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration`.

Sixth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2016-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201604_201606_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Sixth production-root result:

- Covered shards skipped: 15
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2016-06-30
- `tradeability_stk_limit`: 1,005,348 rows, 2,878 entities
- `tradeability_suspension`: 134,582 rows, 2,375 entities
- `tradeability_namechange`: 402 rows, 346 entities

Seventh production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2016-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201607_201609_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Seventh production-root result:

- Covered shards skipped: 18
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2016-09-30
- `tradeability_stk_limit`: 1,190,788 rows, 2,943 entities
- `tradeability_suspension`: 150,223 rows, 2,481 entities
- `tradeability_namechange`: 434 rows, 370 entities

Second three-batch review:

- 2016Q1 through 2016Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 12, 15, and 18 already-covered shards respectively, so continuation is resume-safe and does not waste endpoint quota on completed months.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2016-09-30 with no reported gaps.
- The gate still blocks direct factor generation because the required window is 2015-01-01 through 2025-12-31.
- This is the intended behavior: the process is optimizing away fake profitability from tradeability omissions before replaying old candidates or mining new ones.

Eighth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2016-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201610_201612_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Eighth production-root result:

- Covered shards skipped: 21
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2016-12-31
- `tradeability_stk_limit`: 1,369,466 rows, 3,044 entities
- `tradeability_suspension`: 163,724 rows, 2,600 entities
- `tradeability_namechange`: 468 rows, 397 entities

2015-2016 coverage review:

- 24 monthly shards are covered continuously from 2015-01-01 through 2016-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains a data-readiness milestone, not factor profitability evidence.

Ninth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2017-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201701_201703_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Ninth production-root result:

- Covered shards skipped: 24
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2017-03-31
- `tradeability_stk_limit`: 1,552,694 rows, 3,179 entities
- `tradeability_suspension`: 177,056 rows, 2,726 entities
- `tradeability_namechange`: 540 rows, 436 entities

Tenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2017-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201704_201706_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Tenth production-root result:

- Covered shards skipped: 27
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2017-06-30
- `tradeability_stk_limit`: 1,746,263 rows, 3,291 entities
- `tradeability_suspension`: 193,203 rows, 2,835 entities
- `tradeability_namechange`: 640 rows, 485 entities

Eleventh production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2017-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201707_201709_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Eleventh production-root result:

- Covered shards skipped: 30
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2017-09-30
- `tradeability_stk_limit`: 1,962,493 rows, 3,395 entities
- `tradeability_suspension`: 210,242 rows, 2,943 entities
- `tradeability_namechange`: 664 rows, 503 entities

Third three-batch review:

- 2017Q1 through 2017Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 24, 27, and 30 already-covered shards respectively, so continuation remains resume-safe and quota-efficient.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2017-09-30 with no reported gaps.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This is still the correct direction: the project is removing survivorship/tradeability phantom alpha before replaying old parameters or mining new factor families.

Twelfth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2017-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201710_201712_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twelfth production-root result:

- Covered shards skipped: 33
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2017-12-31
- `tradeability_stk_limit`: 2,168,117 rows, 3,482 entities
- `tradeability_suspension`: 223,968 rows, 3,037 entities
- `tradeability_namechange`: 687 rows, 518 entities

2015-2017 coverage review:

- 36 monthly shards are covered continuously from 2015-01-01 through 2017-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains a data-readiness milestone, not factor profitability evidence.

Thirteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2018-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201801_201803_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirteenth production-root result:

- Covered shards skipped: 36
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2018-03-31
- `tradeability_stk_limit`: 2,373,854 rows, 3,519 entities
- `tradeability_suspension`: 240,058 rows, 3,096 entities
- `tradeability_namechange`: 726 rows, 541 entities

Fourteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2018-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201804_201806_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Fourteenth production-root result:

- Covered shards skipped: 39
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2018-06-30
- `tradeability_stk_limit`: 2,584,809 rows, 3,545 entities
- `tradeability_suspension`: 254,908 rows, 3,137 entities
- `tradeability_namechange`: 833 rows, 587 entities

Fifteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2018-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201807_201809_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Fifteenth production-root result:

- Covered shards skipped: 42
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2018-09-30
- `tradeability_stk_limit`: 2,811,139 rows, 3,569 entities
- `tradeability_suspension`: 263,637 rows, 3,159 entities
- `tradeability_namechange`: 868 rows, 610 entities

Fourth three-batch review:

- 2018Q1 through 2018Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 36, 39, and 42 already-covered shards respectively, so the continuation path remains resume-safe and quota-efficient.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2018-09-30 with no reported gaps.
- 2018 is a necessary A-share bear-market regime segment for later alpha replay, but this backfill itself is not profitability evidence.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.

Sixteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2018-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201810_201812_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Sixteenth production-root result:

- Covered shards skipped: 45
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2018-12-31
- `tradeability_stk_limit`: 3,024,706 rows, 3,587 entities
- `tradeability_suspension`: 266,943 rows, 3,180 entities
- `tradeability_namechange`: 908 rows, 636 entities

2015-2018 coverage review:

- 48 monthly shards are covered continuously from 2015-01-01 through 2018-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This completes the first bear-market regime year in the official tradeability backfill and remains data-readiness evidence, not profitability evidence.

Seventeenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2019-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201901_201903_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Seventeenth production-root result:

- Covered shards skipped: 48
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2019-03-31
- `tradeability_stk_limit`: 3,232,528 rows, 3,620 entities
- `tradeability_suspension`: 268,279 rows, 3,224 entities
- `tradeability_namechange`: 948 rows, 655 entities

Eighteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2019-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201904_201906_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Eighteenth production-root result:

- Covered shards skipped: 51
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2019-06-30
- `tradeability_stk_limit`: 3,451,605 rows, 4,479 entities
- `tradeability_suspension`: 269,970 rows, 3,260 entities
- `tradeability_namechange`: 1,074 rows, 704 entities

Nineteenth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2019-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201907_201909_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Nineteenth production-root result:

- Covered shards skipped: 54
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2019-09-30
- `tradeability_stk_limit`: 3,743,899 rows, 4,571 entities
- `tradeability_suspension`: 271,380 rows, 3,315 entities
- `tradeability_namechange`: 1,109 rows, 718 entities

Fifth three-batch review:

- 2019Q1 through 2019Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 48, 51, and 54 already-covered shards respectively, so the continuation path remains resume-safe and quota-efficient.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2019-09-30 with no reported gaps.
- 2019 is a post-2018 recovery regime segment and is needed for later regime-aware long-cycle factor replay.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.

Twentieth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2019-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_201910_201912_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twentieth production-root result:

- Covered shards skipped: 57
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2019-12-31
- `tradeability_stk_limit`: 4,023,237 rows, 4,690 entities
- `tradeability_suspension`: 272,695 rows, 3,363 entities
- `tradeability_namechange`: 1,149 rows, 739 entities

2015-2019 coverage review:

- 60 monthly shards are covered continuously from 2015-01-01 through 2019-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This adds a post-2018 recovery regime segment to the official tradeability backfill and remains data-readiness evidence, not profitability evidence.

Twenty-first production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2020-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202001_202003_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-first production-root result:

- Covered shards skipped: 60
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2020-03-31
- `tradeability_stk_limit`: 4,295,208 rows, 4,789 entities
- `tradeability_suspension`: 273,629 rows, 3,398 entities
- `tradeability_namechange`: 1,171 rows, 755 entities

Twenty-second production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2020-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202004_202006_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-second production-root result:

- Covered shards skipped: 63
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2020-06-30
- `tradeability_stk_limit`: 4,576,744 rows, 4,898 entities
- `tradeability_suspension`: 276,323 rows, 3,470 entities
- `tradeability_namechange`: 1,346 rows, 823 entities

Twenty-third production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2020-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202007_202009_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-third production-root result:

- Covered shards skipped: 66
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2020-09-30
- `tradeability_stk_limit`: 4,899,385 rows, 5,108 entities
- `tradeability_suspension`: 279,432 rows, 3,585 entities
- `tradeability_namechange`: 1,393 rows, 846 entities

Sixth three-batch review:

- 2020Q1 through 2020Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 60, 63, and 66 already-covered shards respectively, so the long-cycle continuation remains resume-safe and quota-efficient.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2020-09-30 with no reported gaps.
- 2020Q1 contains the COVID crash regime and is mandatory for later long-cycle stress replay; this is still data-readiness evidence, not profitability evidence.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.

Twenty-fourth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2020-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202010_202012_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-fourth production-root result:

- Covered shards skipped: 69
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2020-12-31
- `tradeability_stk_limit`: 5,199,756 rows, 5,236 entities
- `tradeability_suspension`: 282,113 rows, 3,657 entities
- `tradeability_namechange`: 1,442 rows, 875 entities

2015-2020 coverage review:

- 72 monthly shards are covered continuously from 2015-01-01 through 2020-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- The 2020 COVID crash/recovery regime is now included in official tradeability coverage, which is necessary for future long-cycle stress replay.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Twenty-fifth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2021-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202101_202103_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-fifth production-root result:

- Covered shards skipped: 72
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2021-03-31
- `tradeability_stk_limit`: 5,491,812 rows, 5,475 entities
- `tradeability_suspension`: 284,667 rows, 3,718 entities
- `tradeability_namechange`: 1,494 rows, 894 entities

Twenty-sixth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2021-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202104_202106_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-sixth production-root result:

- Covered shards skipped: 75
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2021-06-30
- `tradeability_stk_limit`: 5,805,899 rows, 5,739 entities
- `tradeability_suspension`: 287,351 rows, 3,798 entities
- `tradeability_namechange`: 1,719 rows, 959 entities

Twenty-seventh production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2021-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202107_202109_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-seventh production-root result:

- Covered shards skipped: 78
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2021-09-30
- `tradeability_stk_limit`: 6,154,979 rows, 6,058 entities
- `tradeability_suspension`: 290,356 rows, 3,857 entities
- `tradeability_namechange`: 1,756 rows, 977 entities

Seventh three-batch review:

- 2021Q1 through 2021Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 72, 75, and 78 already-covered shards respectively.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2021-09-30 with no reported gaps.
- 2021 extends the post-COVID recovery and policy/credit normalization regime coverage needed for later long-cycle replay.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.

Twenty-eighth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2021-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202110_202112_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-eighth production-root result:

- Covered shards skipped: 81
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2021-12-31
- `tradeability_stk_limit`: 6,500,984 rows, 6,269 entities
- `tradeability_suspension`: 292,977 rows, 3,911 entities
- `tradeability_namechange`: 1,785 rows, 993 entities

2015-2021 coverage review:

- 84 monthly shards are covered continuously from 2015-01-01 through 2021-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- 2021 post-COVID policy/credit normalization is now included in the official tradeability backfill.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Twenty-ninth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2022-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202201_202203_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Twenty-ninth production-root result:

- Covered shards skipped: 84
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2022-03-31
- `tradeability_stk_limit`: 6,841,382 rows, 6,408 entities
- `tradeability_suspension`: 295,426 rows, 3,945 entities
- `tradeability_namechange`: 1,810 rows, 1,009 entities

Thirtieth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2022-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202204_202206_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirtieth production-root result:

- Covered shards skipped: 87
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2022-06-30
- `tradeability_stk_limit`: 7,194,203 rows, 6,517 entities
- `tradeability_suspension`: 300,006 rows, 4,025 entities
- `tradeability_namechange`: 2,015 rows, 1,070 entities

Thirty-first production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2022-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202207_202209_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-first production-root result:

- Covered shards skipped: 90
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2022-09-30
- `tradeability_stk_limit`: 7,589,504 rows, 6,699 entities
- `tradeability_suspension`: 306,450 rows, 4,071 entities
- `tradeability_namechange`: 2,066 rows, 1,093 entities

Eighth three-batch review:

- 2022Q1 through 2022Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 84, 87, and 90 already-covered shards respectively.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2022-09-30 with no reported gaps.
- 2022 bear/stress regime coverage is now partially included through Q3, which is important for future long-cycle replay and regime robustness checks.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Thirty-second production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2022-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202210_202212_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-second production-root result:

- Covered shards skipped: 93
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2022-12-31
- `tradeability_stk_limit`: 7,963,981 rows, 6,861 entities
- `tradeability_suspension`: 312,153 rows, 4,108 entities
- `tradeability_namechange`: 2,091 rows, 1,101 entities

2015-2022 coverage review:

- 96 monthly shards are covered continuously from 2015-01-01 through 2022-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- 2022 bear/stress regime is now fully included in the official tradeability backfill.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Thirty-third production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2023-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202301_202303_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-third production-root result:

- Covered shards skipped: 96
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2023-03-31
- `tradeability_stk_limit`: 8,339,182 rows, 6,964 entities
- `tradeability_suspension`: 316,082 rows, 4,139 entities
- `tradeability_namechange`: 2,121 rows, 1,118 entities

Thirty-fourth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2023-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202304_202306_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-fourth production-root result:

- Covered shards skipped: 99
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2023-06-30
- `tradeability_stk_limit`: 8,720,707 rows, 7,103 entities
- `tradeability_suspension`: 320,154 rows, 4,179 entities
- `tradeability_namechange`: 2,279 rows, 1,166 entities

Thirty-fifth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2023-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202307_202309_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-fifth production-root result:

- Covered shards skipped: 102
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2023-09-30
- `tradeability_stk_limit`: 9,140,936 rows, 7,246 entities
- `tradeability_suspension`: 322,860 rows, 4,204 entities
- `tradeability_namechange`: 2,301 rows, 1,174 entities

Ninth three-batch review:

- 2023Q1 through 2023Q3 added 9 monthly shards without execution failures.
- `--skip-covered` skipped 96, 99, and 102 already-covered shards respectively.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2023-09-30 with no reported gaps.
- 2023 post-reopening and policy/credit transition coverage is now included through Q3 for future long-cycle replay and regime robustness checks.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Thirty-sixth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2023-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202310_202312_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-sixth production-root result:

- Covered shards skipped: 105
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2023-12-31
- `tradeability_stk_limit`: 9,534,337 rows, 7,342 entities
- `tradeability_suspension`: 324,235 rows, 4,219 entities
- `tradeability_namechange`: 2,333 rows, 1,194 entities

2015-2023 coverage review:

- 108 monthly shards are covered continuously from 2015-01-01 through 2023-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- 2023 post-reopening, liquidity-transition, and policy-transition regimes are now included in the official tradeability backfill.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Thirty-seventh production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2024-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202401_202403_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-seventh production-root result:

- Covered shards skipped: 108
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2024-03-31
- `tradeability_stk_limit`: 9,925,519 rows, 7,416 entities
- `tradeability_suspension`: 324,871 rows, 4,222 entities
- `tradeability_namechange`: 2,343 rows, 1,197 entities

Thirty-eighth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2024-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202404_202406_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-eighth production-root result:

- Covered shards skipped: 111
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2024-06-30
- `tradeability_stk_limit`: 10,327,692 rows, 7,482 entities
- `tradeability_suspension`: 326,020 rows, 4,233 entities
- `tradeability_namechange`: 2,493 rows, 1,242 entities

Thirty-ninth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2024-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202407_202409_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Thirty-ninth production-root result:

- Covered shards skipped: 114
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2024-09-30
- `tradeability_stk_limit`: 10,767,306 rows, 7,545 entities
- `tradeability_suspension`: 327,158 rows, 4,244 entities
- `tradeability_namechange`: 2,532 rows, 1,257 entities

Tenth three-batch review:

- 2024Q1 through 2024Q3 added 9 monthly shards without execution failures or warnings.
- `--skip-covered` skipped 108, 111, and 114 already-covered shards respectively.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2024-09-30 with no reported gaps.
- 2024 policy, liquidity, and market-style transition coverage is now included through Q3 for future long-cycle replay and regime robustness checks.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Fortieth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2024-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202410_202412_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Fortieth production-root result:

- Covered shards skipped: 117
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2024-12-31
- `tradeability_stk_limit`: 11,189,468 rows, 7,637 entities
- `tradeability_suspension`: 327,967 rows, 4,265 entities
- `tradeability_namechange`: 2,556 rows, 1,270 entities

2015-2024 coverage review:

- 120 monthly shards are covered continuously from 2015-01-01 through 2024-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- Full-year 2024 coverage is now included for future long-cycle same-parameter replay, regime coverage checks, and tradeability-mask integration.
- Direct factor generation remains blocked because the expected full window is 2015-01-01 through 2025-12-31.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Forty-first production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2025-03-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202501_202503_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Forty-first production-root result:

- Covered shards skipped: 120
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest target: 2015-01-01 to 2025-03-31

Forty-second production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2025-06-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202504_202506_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Forty-second production-root result:

- Covered shards skipped: 123
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest target: 2015-01-01 to 2025-06-30

Forty-third production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2025-09-30 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202507_202509_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Forty-third production-root result:

- Covered shards skipped: 126
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2025-09-30
- `tradeability_stk_limit`: 12,494,589 rows, 8,022 entities
- `tradeability_suspension`: 331,110 rows, 4,347 entities
- `tradeability_namechange`: 2,835 rows, 1,382 entities

Eleventh three-batch review:

- 2025Q1 through 2025Q3 added 9 monthly shards without execution failures or warnings.
- `--skip-covered` skipped 120, 123, and 126 already-covered shards respectively.
- Manifest coverage remains one continuous merged interval from 2015-01-01 through 2025-09-30 with no reported gaps.
- Direct factor generation remains blocked because the final expected quarter, 2025Q4, is not yet covered.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Forty-fourth production-root batch:

```powershell
python scripts\run_tushare_tradeability_backfill_plan.py --start-date 2015-01-01 --end-date 2025-12-31 --processed-root data\processed\round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data\reports\round198_tradeability_long_cycle_official_backfill_execute_202510_202512_20260623 --report-root data\reports\round198_tradeability_long_cycle_official_backfill_execute_shards_20260623 --max-shards 3 --snapshot 2026-06-23 --skip-covered --execute --execute-write-processed
```

Forty-fourth production-root result:

- Covered shards skipped: 129
- Executed shards: 3
- Passed shards: 3
- Failed shards: 0
- Coverage manifest: 2015-01-01 to 2025-12-31
- `tradeability_stk_limit`: 12,936,279 rows, 8,130 entities
- `tradeability_suspension`: 332,011 rows, 4,373 entities
- `tradeability_namechange`: 2,878 rows, 1,404 entities

2015-2025 full-window coverage review:

- 132 monthly shards are covered continuously from 2015-01-01 through 2025-12-31.
- The coverage manifest reports one merged interval and no gaps for `tradeability_stk_limit`, `tradeability_suspension`, `tradeability_namechange`, and `stock_basic_status_snapshot`.
- The readiness audit reports 0 blocking tradeability controls and marks `limit_up_down_filter`, `suspension_filter`, `st_flag_filter`, `new_listing_age_filter`, `delisting_risk_filter`, and `board_permission_filter` usable for direct mining at the data-readiness layer.
- This clears the official-feed coverage blocker, but it does not by itself prove that every factor matrix and portfolio path applies the official masks.
- This remains data-readiness evidence and process-control evidence, not profitability evidence.

Official mask integration step:

- `src/quant_robot/ops/cn_stock_tradeability_gate.py` now accepts optional official `stk_limit`, `suspension`, and `namechange` frames.
- Official `stk_limit` rows set `limit_up_official` and `limit_down_official`, blocking buys at official up-limit closes and sells at official down-limit closes.
- Official `suspend_d` rows set `suspended_official`, blocking both buy and sell.
- Official `namechange` rows set `st_flag_official` over available/effective ST-name intervals, blocking both buy and sell through the existing `st_flag`.
- `scripts/run_cn_stock_tradeability_gate.py` now exposes `--stk-limit-path`, `--suspension-path`, and `--namechange-path` for repeatable local reports.
- Unit coverage: `python -m unittest tests.unit.test_cn_stock_tradeability_gate tests.unit.test_cn_stock_tradeability_gate_cli`.
- Remaining blocker: factor-matrix and portfolio-construction paths still need explicit official-mask join smoke before the quality gate should mark these controls fully implemented.

Official factor-matrix and portfolio smoke:

- Added `src/quant_robot/ops/cn_stock_tradeability_mask_join_smoke.py` to join official tradeability masks into factor rows and portfolio execution bars before calling the shared factor backtest.
- Added `scripts/run_cn_stock_tradeability_mask_join_smoke.py` for repeatable local smoke reports using CSV or Parquet inputs.
- The backtest engine now accepts optional `entry_tradeable` and `exit_tradeable` columns: untradeable entries are filtered, and untradeable planned exits are delayed to the next sellable bar rather than optimistically skipped.
- Unit coverage: `python -m unittest tests.unit.test_backtest tests.unit.test_cn_stock_tradeability_mask_join_smoke tests.unit.test_cn_stock_tradeability_mask_join_smoke_cli`.
- Real-sample smoke output: `data/reports/round198_tradeability_mask_join_smoke_real_sample_20260623`.
- Real-sample smoke summary: 3 factor rows, 3 rows with joined tradeability masks, factor-matrix join pass, portfolio execution mask pass, 54 official mask-hit rows, 0 executed trades, and 3 trades filtered by entry tradeability.
- Interpretation: 0 executed trades is the expected result for this deliberately selected limit-hit sample because the official masks blocked impossible entries. This is process-control evidence, not profitability evidence.
- Remaining blocker: old candidate factors and frozen parameters still need full 2015-2025 replay with the official masks before any promotion or profitability claim.

First old-candidate masked replay:

- Candidate: Round126 frozen `turnover_rate_f_low_participation_budget_100k_20`.
- Output: `data/reports/round198_turnover_repair_champion_official_mask_replay_exitcap_20260623`.
- Frozen parameters: TopN 100, holding 20, rebalance 20, execution lag 1, cost 10 bps, market impact 10 bps, portfolio value 100k, max calendar holding 45 days.
- Window: 2015-01-01 through 2025-12-31.
- Signal rows: 504,989; executed trades: 11,091.
- Official tradeability impact: 2,106 entries filtered, 17 exits filtered, 22 exits delayed, 2,123 total tradeability-filtered trades, maximum accepted tradeability exit delay 4 days after calendar-cap truncation.
- Result: total return 647.88%, annualized return 11.87%, Sharpe 0.244, overlap-adjusted Sharpe 0.247, Newey-West t-stat 1.046, max drawdown -59.55%, win rate 54.9%.
- Blockers: `overlap_adjusted_sharpe_below_min`, `calendar_holding_gate_filtered_trades`, `extreme_trade_return_present`, `max_drawdown_below_user_floor`.
- Decision: 0 walk-forward-allowed candidates and 0 promotion candidates. Keep the low-turnover repair family hibernated.
- Engineering note: the first full-window official-mask replay used a whole-table merge and took roughly 9-10 minutes with peak memory around 26GB for one case. Continue old-candidate replay only after adding chunked/year-sliced reuse so the process does not waste compute on repeated full-table joins.

Year-sliced tradeability mask cache:

- Added `src/quant_robot/ops/cn_stock_tradeability_mask_cache.py`.
- Added `scripts/run_cn_stock_tradeability_mask_cache.py`.
- The cache writes reusable masks under `processed/tradeability_masks/frequency=1d/market=CN/year=<year>/part-00000.parquet`.
- The old-candidate portfolio conversion CLI now accepts `--tradeability-mask-path`, so repeated replay can reuse precomputed masks instead of rebuilding official joins inside every case.
- Unit coverage includes `tests.unit.test_cn_stock_tradeability_mask_cache`, `tests.unit.test_cn_stock_tradeability_mask_cache_cli`, and the `tradeability_mask_path` CLI path in `tests.unit.test_turnover_repair_champion_portfolio_conversion_cli`.

2025 cache smoke:

```powershell
python scripts\run_cn_stock_tradeability_mask_cache.py --bars-path data\processed\office_desktop_20260616_combined_research\processed\bars --stk-limit-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_stk_limit --suspension-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_suspension --namechange-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_namechange --output-root data\processed\round198_tradeability_mask_cache_smoke_20260623 --year 2025
```

2025 cache result:

- Output: `data/processed/round198_tradeability_mask_cache_smoke_20260623`.
- Rows: 1,308,492.
- Years: `[2025]`.
- Entry-blocked rows: 571,971.
- Exit-blocked rows: 563,017.
- Official mask-hit rows: 46,559.
- Written files: 1.
- Note: blocked rows include official masks plus board-permission and other policy blocks; official mask-hit rows isolate rows touched by official suspension/limit/ST feeds.

2025 cached replay smoke:

```powershell
python scripts\run_turnover_repair_champion_portfolio_conversion.py --output-dir data\reports\round198_turnover_repair_champion_mask_cache_replay_2025_smoke_20260623 --analysis-start-date 2025-01-01 --analysis-end-date 2025-12-31 --factor-input-root configs\cn_stock_authority_daily_basic_inputs_2015_2025.json --cost-bps-values 10 --portfolio-values 100000 --top-n 100 --holding-period 20 --rebalance-interval 20 --execution-lag 1 --min-signal-amount 10000000 --min-signal-date-amount 10000000 --max-participation-rate 0.01 --market-impact-bps 10 --max-calendar-holding-days 45 --min-overlap-adjusted-sharpe 0.5 --max-drawdown-floor -0.4 --tradeability-mask-path data\processed\round198_tradeability_mask_cache_smoke_20260623\processed\tradeability_masks
```

2025 cached replay result:

- Output: `data/reports/round198_turnover_repair_champion_mask_cache_replay_2025_smoke_20260623`.
- Signal rows: 64,487.
- Signal dates: 12.
- Executed trades: 913.
- Total return: 1,385.78%.
- Annualized return: 864.81%.
- Sharpe: 0.956.
- Overlap-adjusted Sharpe: 1.987.
- Newey-West t-stat: 2.168.
- Max drawdown: -2.18%.
- Win rate: 73.33%.
- Tradeability impact: 183 entries filtered, 3 exits filtered, 1 delayed exit, 186 total tradeability-filtered trades, max exit delay 4 days.
- Blocker: `extreme_trade_return_present`.
- Decision: 0 walk-forward candidates and 0 promotion candidates.

Interpretation:

- The 2025 cached replay is deliberately treated as a path smoke only. It covers one calendar year and only 12 signal dates, so it can be dominated by a single regime and a small number of extreme trades.
- The high 2025 total return and annualized return must not be used as profitability evidence.
- The useful result is engineering evidence: the reusable cache path works, replay time dropped to about one minute for a 2025 slice, and the gate correctly keeps a short-window high-return result rejected.
- Superseded caveat: this 2025 cache smoke was generated before the cross-year `namechange` interval fix below. Keep it only as historical path-smoke evidence, not as canonical cache evidence.

Full-window cache defect and fix:

- Defect found during cache-vs-direct audit: the year-sliced cache CLI read `namechange` with a requested-year partition filter. This missed prior-year ST/namechange intervals that were still active in the requested year.
- Example audit: for 2023, direct official construction had 40,929 `st_flag_official` rows, while the old cache had only 12,771. `stk_limit` and `suspend_d` matched, isolating the defect to cross-year ST interval handling.
- Fix: `scripts/run_cn_stock_tradeability_mask_cache.py` now reads the full `namechange` interval table for every requested cache year while keeping high-frequency `stk_limit`, `suspension`, and bars year-sliced.
- Regression test: `test_cli_keeps_prior_year_namechange_interval_active_in_requested_year`.
- Startup protocol now requires both `tradeability_mask_cache_cross_year_namechange_interval_check` and `tradeability_cache_direct_equivalence_check_before_profit_claims`.

Corrected full-window mask cache:

```powershell
python scripts\run_cn_stock_tradeability_mask_cache.py --bars-path data\processed\cn_stock_long_history_2015_202306\processed\bars --bars-path data\processed\office_desktop_20260616_combined_research\processed\bars --stk-limit-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_stk_limit --suspension-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_suspension --namechange-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_namechange --output-root data\processed\round198_tradeability_mask_cache_2015_2025_20260623 --year 2015 --year 2016 --year 2017 --year 2018 --year 2019 --year 2020 --year 2021 --year 2022 --year 2023 --year 2024 --year 2025
```

Corrected cache result:

- Output: `data/processed/round198_tradeability_mask_cache_2015_2025_20260623`.
- Rows: 10,785,537.
- Years: `[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]`.
- Entry-blocked rows: 3,772,645.
- Exit-blocked rows: 3,710,296.
- Official mask-hit rows: 613,142.
- Written files: 11.
- 2025 corrected cache slice: 1,308,492 rows, 597,018 entry-blocked rows, 588,681 exit-blocked rows, 74,650 official mask-hit rows, including 53,776 ST official hits.

Cache/direct equivalence check:

- 2023 direct official path versus corrected cache: 1,258,734 matched keys, 0 missing keys, 0 duplicate keys.
- Field differences: `entry_tradeable` 0, `exit_tradeable` 0, `suspended_official` 0, `limit_up_official` 0, `limit_down_official` 0, `st_flag_official` 0, `blocked_reasons` 0.
- Interpretation: the corrected year-sliced cache is now equivalent to direct official construction for the audited split-year sample and can be used as the repeatable replay path, subject to the same parity spot check before profit claims.

Corrected full-window cached replay:

```powershell
python scripts\run_turnover_repair_champion_portfolio_conversion.py --output-dir data\reports\round198_turnover_repair_champion_mask_cache_replay_full_fixed_st_20260623 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --factor-input-root configs\cn_stock_authority_daily_basic_inputs_2015_2025.json --cost-bps-values 10 --portfolio-values 100000 --top-n 100 --holding-period 20 --rebalance-interval 20 --execution-lag 1 --min-signal-amount 10000000 --min-signal-date-amount 10000000 --max-participation-rate 0.01 --market-impact-bps 10 --max-calendar-holding-days 45 --min-overlap-adjusted-sharpe 0.5 --max-drawdown-floor -0.4 --tradeability-mask-path data\processed\round198_tradeability_mask_cache_2015_2025_20260623\processed\tradeability_masks
```

Corrected cached replay result:

- Output: `data/reports/round198_turnover_repair_champion_mask_cache_replay_full_fixed_st_20260623`.
- The replay JSON now records `input_paths`, including bars roots, factor input config, and `tradeability_mask_path`, so future audits can verify which official-mask cache was used.
- Runtime: about 116 seconds for one frozen candidate replay.
- Signal rows: 504,989.
- Signal dates: 134.
- Executed trades: 11,091.
- Total return: 647.88%.
- Annualized return: 11.87%.
- Sharpe: 0.244.
- Overlap-adjusted Sharpe: 0.247.
- Newey-West t-stat: 1.046.
- Max drawdown: -59.55%.
- Win rate: 54.87%.
- Tradeability impact: 2,106 entries filtered, 17 exits filtered, 22 delayed exits, 2,123 total tradeability-filtered trades, max exit delay 4 days.
- Blockers: `overlap_adjusted_sharpe_below_min`, `calendar_holding_gate_filtered_trades`, `extreme_trade_return_present`, `max_drawdown_below_user_floor`.
- Decision: 0 walk-forward candidates and 0 promotion candidates. The corrected cache reproduced the direct official replay and kept the candidate rejected.

Metadata-complete full-window cache correction:

- Follow-up defect: the corrected cache above still did not pass `stock_basic` into the cache build command, so `entry_tradeable` and `exit_tradeable` did not include new-listing, delisted/inactive, or board-permission blocks.
- Fix: `src/quant_robot/ops/cn_stock_tradeability_mask_cache.py` now writes and summarizes `new_listing_flag`, `delisted_or_inactive_flag`, and `board_permission_blocked`; startup now requires `stock_basic` L/D/P metadata and metadata blocker counts before old-candidate replay or new profitability claims.
- Regression tests:
  - `test_mask_cache_carries_stock_basic_metadata_blocks`
  - `test_cli_stock_basic_path_blocks_delisted_rows_in_requested_year`
  - startup protocol assertions for `tradeability_mask_cache_stock_basic_l_d_p_status_required` and `tradeability_mask_cache_metadata_blocker_counts_required`.

Metadata-complete cache command:

```powershell
python scripts\run_cn_stock_tradeability_mask_cache.py --bars-path data\processed\cn_stock_long_history_2015_202306\processed\bars --bars-path data\processed\office_desktop_20260616_combined_research\processed\bars --stock-basic-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\metadata\tushare_stock_basic --stk-limit-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_stk_limit --suspension-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_suspension --namechange-path data\processed\round198_tradeability_long_cycle_official_backfill_20260623\processed\tradeability_namechange --output-root data\processed\round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623 --year 2015 --year 2016 --year 2017 --year 2018 --year 2019 --year 2020 --year 2021 --year 2022 --year 2023 --year 2024 --year 2025
```

Metadata-complete cache result:

- Output: `data/processed/round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623`.
- Rows: 10,785,537.
- Years: `[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]`.
- Stock basic supplied for all years: true.
- Entry-blocked rows: 4,428,680.
- Exit-blocked rows: 4,380,619.
- Official mask-hit rows: 613,142.
- Metadata mask-hit rows: 3,739,869.
- Metadata blockers: 323,923 new-listing rows, 399,967 delisted/inactive rows, 3,317,705 board-permission rows.
- Written files: 11.

Metadata-complete cache/direct equivalence check:

- 2023 direct path versus metadata-complete cache: 1,258,734 matched keys, 0 missing keys, 0 duplicate keys.
- Field differences: `entry_tradeable` 0, `exit_tradeable` 0, `suspended_official` 0, `limit_up_official` 0, `limit_down_official` 0, `st_flag_official` 0, `new_listing_flag` 0, `delisted_or_inactive_flag` 0, `board_permission_blocked` 0, `blocked_reasons` 0.
- 2023 metadata blockers in both direct and cache paths: 29,440 new-listing rows, 25,495 delisted/inactive rows, and 489,056 board-permission rows.

Metadata-complete Round126 replay:

```powershell
python scripts\run_turnover_repair_champion_portfolio_conversion.py --output-dir data\reports\round199_turnover_repair_champion_metadata_mask_cache_replay_full_20260623 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --factor-input-root configs\cn_stock_authority_daily_basic_inputs_2015_2025.json --cost-bps-values 10 --portfolio-values 100000 --top-n 100 --holding-period 20 --rebalance-interval 20 --execution-lag 1 --min-signal-amount 10000000 --min-signal-date-amount 10000000 --max-participation-rate 0.01 --market-impact-bps 10 --max-calendar-holding-days 45 --min-overlap-adjusted-sharpe 0.5 --max-drawdown-floor -0.4 --tradeability-mask-path data\processed\round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623\processed\tradeability_masks
```

Metadata-complete replay result:

- Output: `data/reports/round199_turnover_repair_champion_metadata_mask_cache_replay_full_20260623`.
- Signal rows: 504,989.
- Signal dates: 134.
- Executed trades: 10,452.
- Total return: 670.36%.
- Annualized return: 12.84%.
- Sharpe: 0.251.
- Overlap-adjusted Sharpe: 0.255.
- Newey-West t-stat: 1.048.
- Max drawdown: -58.49%.
- Win rate: 53.52%.
- Tradeability impact: 2,760 entries filtered, 13 exits filtered, 19 delayed exits, 2,773 total tradeability-filtered trades, max exit delay 4 days.
- Blockers: `overlap_adjusted_sharpe_below_min`, `calendar_holding_gate_filtered_trades`, `extreme_trade_return_present`, `max_drawdown_below_user_floor`.
- Decision: 0 walk-forward candidates and 0 promotion candidates. High total return remains insufficient because overlap-adjusted quality, extreme-trade, calendar-holding, and drawdown blockers remain.

## Decision

Do not claim any CN stock factor profitability from this backfill. The next valid work is:

1. Use only the corrected full-window 2015-2025 official tradeability mask cache for old-candidate replay and new CN stock profitability claims.
2. The canonical cache is now the Round199 metadata-complete cache with `stock_basic` L/D/P, official `stk_limit`, `suspend_d`, and full-interval `namechange`. Do not use the no-stock-basic cache as complete tradeability evidence.
3. Confirm new-listing, delist/inactive, board-permission, cross-year `namechange`/ST interval coverage, metadata blocker counts, and direct-vs-cache equivalence before each new replay package.
4. Treat the corrected Round126 replay as rejected evidence: high total return did not overcome overlap Sharpe, drawdown, extreme-trade, and calendar-holding blockers.
5. Resume CN stock factor mining only on full-window, masked, costed data with startup, quality, and candidate-plan gates cleared.

This is data-readiness and process-control evidence, not profitability evidence.
