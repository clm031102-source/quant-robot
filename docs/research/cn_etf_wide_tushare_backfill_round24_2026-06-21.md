# CN ETF Wide Tushare Backfill Round 24

Date: 2026-06-21

## Purpose

Round 24 backfilled 2020 into the wide CN ETF Tushare root.

This extends the ETF rotation research dataset through the 2020 COVID shock window before any new broad ETF factor mining.

## 2020 Backfill Result

Root:

- `data/processed/tushare_etf_wide_history_2023_2026`

Window:

- 2020-01-02 to 2020-12-31

Result:

- Processed rows: 191,775
- Assets: 985
- Duplicate bars: 0
- Zero-volume rows: 0
- Missing asset-date rows: 22,540
- Stale-price rows: 6,498
- Extreme-return rows: 20
- Skipped trade dates: 0
- Empty raw trade dates: 2
  - 2020-05-28
  - 2020-06-03

## Combined Wide Root After Round 24

Summary:

- Rows: 1,119,490
- Assets: 1,781
- Date range: 2020-01-02 to 2024-06-28
- Trading dates: 1,085
- Assets with at least 756 dates: 756
- Assets with at least 882 dates: 552
- Assets with at least 1,000 dates: 464

By year:

| Year | Rows | Assets | Dates |
|---:|---:|---:|---:|
| 2020 | 191,775 | 985 | 241 |
| 2021 | 217,179 | 1,098 | 243 |
| 2022 | 266,284 | 1,233 | 242 |
| 2023 | 290,149 | 1,370 | 242 |
| 2024 | 154,103 | 1,431 | 117 |

Coverage quantiles by asset:

- 10%: 117 dates
- 25%: 240 dates
- 50%: 688 dates
- 75%: 1,016 dates
- 90%: 1,085 dates
- 95%: 1,085 dates

## Interpretation

The root now clears the minimum length needed for the existing 756-train / 126-test rolling walk-forward profile:

- Available: 1,085 trading dates
- Required for at least one strict fold: 882 trading dates

This makes the dataset long enough to start filtered ETF walk-forward experiments.

It is still not safe to mine directly on the raw broad universe.

## Data-Quality Warning

The raw universe contains many short-history ETFs and stale-price rows. Direct TopN factor selection can still manufacture false positives from:

- newly listed ETFs,
- stale or thinly traded instruments,
- abnormal one-day returns,
- incomplete coverage across train/test folds.

The next round must build or run a liquid-continuous ETF universe filter before broad factor mining resumes.

## Decision

Round 25 should implement or run a liquid-continuous universe filter with:

- minimum history coverage,
- minimum recent amount or volume,
- stale-price exclusion,
- extreme-return quarantine,
- enough tradable names in every train/test fold.

Only after this gate passes should Round 26 run public ETF factor families such as dual momentum, volatility-adjusted momentum, low-volatility trend, drawdown recovery, and breadth/risk-on overlays.

## Current Conclusion

Round 24 produced 0 new factor names and 0 promotable factors.

It completed the minimum ETF data length foundation: 1,119,490 rows across 1,781 ETFs from 2020-01-02 to 2024-06-28.
