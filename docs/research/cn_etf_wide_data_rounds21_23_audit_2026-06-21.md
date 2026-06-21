# CN ETF Wide Data Rounds 21-23 Audit

Date: 2026-06-21

## Scope

This audit covers:

- Round 21: local CN ETF data audit and 2023 + 2024H1 Tushare wide ETF backfill
- Round 22: CN ETF empty-response pipeline fix and 2022 backfill
- Round 23: 2021 backfill

This implements the standing rule: every 3 rounds, review the prior work and adjust direction.

## Results

| Round | Work | New factor names | Promotable factors | Main outcome |
|---:|---|---:|---:|---|
| 21 | Audited ETF data roots; built 2023 + 2024H1 wide ETF root | 0 | 0 | 444,252 rows, 1,466 ETFs |
| 22 | Fixed CN_ETF empty response handling; backfilled 2022 | 0 | 0 | 710,536 rows, 1,498 ETFs |
| 23 | Backfilled 2021 | 0 | 0 | 927,715 rows, 1,527 ETFs |

Current combined root:

- `data/processed/tushare_etf_wide_history_2023_2026`

Current coverage:

- Date range: 2021-01-04 to 2024-06-28
- Trading dates: 844
- Rows: 927,715
- Assets: 1,527

## Audit Judgment

This was the right direction.

The previous ETF factor attempts were limited by a narrow 10-ETF universe. The project now has a broad ETF dataset that can eventually support ETF rotation research with enough breadth and capacity.

However, this is still not a factor-discovery success. It is data infrastructure needed to avoid wasting future factor-mining cycles.

## Why Not Mine Immediately

The current wide root is still not ready for promotion-grade factor mining.

Reasons:

- 844 trading dates are below the current strict rolling profile requirement of 882 dates.
- The universe includes many short-history ETFs.
- Stale-price rows and extreme-return rows exist.
- Liquidity / continuity filters are not yet applied.
- Raw broad ETF selection can manufacture false winners from stale or newly listed assets.

## Direction Change

Stop:

- Running ETF walk-forward on the 10-ETF CSV root for serious validation.
- Mining broad ETF factors without liquidity/continuity filters.
- Treating data breadth alone as signal quality.

Continue:

- Wide Tushare ETF history backfill.
- Data-quality filtering before factor grids.
- Public, economically interpretable ETF factor families after data is fit for purpose.

Next:

1. Round 24 backfill 2020 into the same wide ETF root.
2. Then build or run a liquid-continuous ETF universe filter:
   - minimum coverage days,
   - minimum recent amount / volume,
   - stale-price exclusion,
   - extreme-return quarantine,
   - benchmark ETF inclusion.
3. Only then run a small public ETF rotation grid:
   - relative strength / dual momentum,
   - volatility-adjusted momentum,
   - low-volatility trend,
   - drawdown recovery,
   - breadth/risk-on overlay.

## Conclusion

Rounds 21-23 produced no factor and no promotable signal.

They corrected the project direction: before mining ETF rotation factors, the project needs a broad, clean, sufficiently long ETF universe. The next work should continue data completion and filtering rather than chasing another indicator on weak data.
