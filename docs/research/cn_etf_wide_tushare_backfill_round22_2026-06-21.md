# CN ETF Wide Tushare Backfill Round 22

Date: 2026-06-21

## Purpose

Round 22 continued the wide CN ETF history build and fixed a data-pipeline blocker found during the 2022 backfill.

## Pipeline Issue Found

The first 2022 ingest attempt stopped on:

- `empty raw response for open trade date 20220126`

Root cause:

- `run_tushare_daily_ingest` treated every open-date empty response as fatal.
- That behavior is appropriate for CN stock daily bars, but too strict for historical CN ETF `fund_daily`, where individual historical open dates can return empty responses.

## Code Fix

Updated:

- `src/quant_robot/data/ingest/tushare_pipeline.py`
- `tests/unit/test_tushare_ingest_pipeline.py`

New behavior:

- CN stock empty daily responses still fail fast.
- CN ETF empty `fund_daily` responses are recorded in the manifest as failed empty dates and exposed in `empty_raw_trade_dates`, while the ingest continues.

Verification:

```powershell
python -m unittest tests.unit.test_tushare_ingest_pipeline
```

Result:

- 16 tests passed.

## 2022 Backfill Result

Command target:

- `data/processed/tushare_etf_wide_history_2023_2026`

Window:

- 2022-01-04 to 2022-12-30

Result:

- Downloaded trade dates: 242
- Skipped trade dates: 0
- Empty raw trade dates: 0 on retry
- Processed rows: 266,284
- Assets: 1,233
- Duplicate bars: 0
- Zero-volume rows: 0
- Missing asset-date rows: 10,752
- Stale-price rows: 2,853
- Extreme-return rows: 10

## Combined Wide Root After Round 22

Root:

- `data/processed/tushare_etf_wide_history_2023_2026`

Summary:

- Rows: 710,536
- Assets: 1,498
- Date range: 2022-01-04 to 2024-06-28
- Trading dates: 601

By year:

| Year | Rows | Assets | Dates |
|---:|---:|---:|---:|
| 2022 | 266,284 | 1,233 | 242 |
| 2023 | 290,149 | 1,370 | 242 |
| 2024 | 154,103 | 1,431 | 117 |

Coverage quantiles by asset:

- 10%: 160.7 dates
- 25%: 363.75 dates
- 50%: 596 dates
- 75%: 601 dates
- 90%: 601 dates

## Interpretation

The wide ETF history build is now viable.

The project has moved from:

- 10 ETFs over long history

to:

- 1,498 ETFs over 2022-2024H1.

This is a better foundation, but still not enough for promotion-grade walk-forward validation. It needs at least more 2021/2020 history and a liquid-continuous universe filter before serious factor mining.

## Next Direction

Round 23 should backfill 2021 into the same root.

After Round 23, perform the required three-round audit for Rounds 21-23 and decide whether to:

- keep backfilling to 2020/2019, or
- pause and implement a liquid-continuous ETF universe filter first.

## Current Conclusion

Round 22 produced 0 new factor names and 0 promotable factors.

It fixed a real ETF data-pipeline blocker and expanded the wide CN ETF dataset to 710,536 rows across 1,498 ETFs.
