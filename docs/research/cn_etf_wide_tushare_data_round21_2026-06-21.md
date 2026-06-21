# CN ETF Wide Tushare Data Round 21

Date: 2026-06-21

## Purpose

Round 21 audited why recent ETF factor mining had weak validation power, then started building the missing data foundation.

Finding:

- `data/processed/etf_csv` has long history but only 10 ETFs.
- Existing wide Tushare ETF data has 1,300+ ETFs, but only short 2024 samples.
- The practical ETF-rotation project needs wide ETF history before more serious ETF factor validation.

## Local Data Audit

Processed CN ETF roots found:

| Root | Rows | Assets | Start | End | Comment |
|---|---:|---:|---|---|---|
| `data/processed/tushare_realdata_20260615_medium_2024h1` | 154,103 | 1,431 | 2024-01-02 | 2024-06-28 | Wide, short sample |
| `data/processed/tushare_realdata_20260615_sample` | 11,418 | 1,338 | 2024-01-02 | 2024-01-12 | Wide, smoke sample |
| `data/processed/etf_csv` | 21,798 | 10 | 2011-12-09 | 2026-05-22 | Long, narrow sample |

## New Wide ETF Backfill

New local-only data root:

- `data/processed/tushare_etf_wide_history_2023_2026`

Downloaded and processed:

| Window | Trade dates | Rows | Assets | Quality notes |
|---|---:|---:|---:|---|
| 2023-01-03 to 2023-12-29 | 242 | 290,149 | 1,370 | 0 duplicate bars, 0 zero-volume rows, 13,774 missing asset-date rows, 3,636 stale-price rows, 4 extreme-return rows |
| 2024-01-02 to 2024-06-28 | 117 | 154,103 | 1,431 | 0 duplicate bars, 0 zero-volume rows, 6,008 missing asset-date rows, 1,816 stale-price rows, 3 extreme-return rows |

Combined root summary after both chunks:

- Rows: 444,252
- Assets: 1,466
- Date range: 2023-01-03 to 2024-06-28
- Trading dates: 359
- Coverage quantiles by asset:
  - 10%: 128 dates
  - 25%: 291.25 dates
  - 50%: 359 dates
  - 75%: 359 dates
  - 90%: 359 dates

## Interpretation

This data direction is more useful than continuing to mine 10-ETF strategies.

The wide Tushare ETF dataset solves the narrow-universe problem, but it introduces a new quality problem:

- many ETFs are newly listed or short-history,
- some stale-price rows exist,
- a few extreme-return rows need audit,
- broad-universe ETF mining must filter for coverage and liquidity before backtesting.

## Decision

Continue wide ETF history backfill before serious ETF factor mining.

Do not run promotion-grade walk-forward on this root yet because 2023-2024H1 is too short.

Use this root for:

- data-quality filtering design,
- quick exploratory sanity checks only,
- building a liquid continuous ETF universe.

Do not use it for:

- paper-ready claims,
- live signals,
- final profitability claims.

## Next Direction

Round 22 should backfill 2022 into the same wide ETF root, then continue toward 2021/2020 so the project can support multi-year walk-forward validation on a broad ETF universe.

After enough history exists, the next factor families should be public and economically interpretable:

- relative strength / dual momentum,
- volatility-adjusted momentum,
- low-volatility trend,
- drawdown recovery,
- breadth/risk-on overlays,
- crash-protection cash filters.

## Current Conclusion

Round 21 produced 0 new factor names and 0 promotable factors.

It produced a materially better data foundation for future ETF factor mining: a wide Tushare ETF root with 1,466 assets over 2023-2024H1.
