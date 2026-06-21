# CN ETF Wide Tushare Backfill Round 23

Date: 2026-06-21

## Purpose

Round 23 backfilled 2021 into the wide CN ETF Tushare root.

This continued the data-foundation work needed before broad ETF rotation factor mining.

## 2021 Backfill Result

Root:

- `data/processed/tushare_etf_wide_history_2023_2026`

Window:

- 2021-01-04 to 2021-12-31

Result:

- Downloaded trade dates: 243
- Skipped trade dates: 0
- Empty raw trade dates: 0
- Processed rows: 217,179
- Assets: 1,098
- Duplicate bars: 0
- Zero-volume rows: 0
- Missing asset-date rows: 7,949
- Stale-price rows: 2,770
- Extreme-return rows: 18

## Combined Wide Root After Round 23

Summary:

- Rows: 927,715
- Assets: 1,527
- Date range: 2021-01-04 to 2024-06-28
- Trading dates: 844

By year:

| Year | Rows | Assets | Dates |
|---:|---:|---:|---:|
| 2021 | 217,179 | 1,098 | 243 |
| 2022 | 266,284 | 1,233 | 242 |
| 2023 | 290,149 | 1,370 | 242 |
| 2024 | 154,103 | 1,431 | 117 |

Coverage quantiles by asset:

- 10%: 159.6 dates
- 25%: 414 dates
- 50%: 724 dates
- 75%: 842 dates
- 90%: 844 dates

## Interpretation

The wide ETF root is now close to the minimum length needed for the existing 756-train / 126-test rolling walk-forward profile.

Current dates:

- 844 trading dates

Required for at least one current strict fold:

- 756 train days + 126 test days = 882 trading dates

Gap:

- about 38 trading dates

Therefore, the next step should be 2020 backfill, not signal mining.

## Data-Quality Warning

This broad ETF universe is not yet safe to use raw.

Reasons:

- Many ETFs have short listing histories.
- Some stale-price rows exist each year.
- Extreme-return rows exist and need audit/filtering.
- A broad ETF backtest without a liquid-continuous universe filter can select bad or stale instruments.

## Decision

Do not mine broad ETF factors on this root yet.

Round 24 should backfill 2020, then run a data-quality / continuous-liquidity universe filter before any factor grid.

## Current Conclusion

Round 23 produced 0 new factor names and 0 promotable factors.

It expanded the wide CN ETF dataset to 927,715 rows across 1,527 ETFs from 2021-01-04 to 2024-06-28.
