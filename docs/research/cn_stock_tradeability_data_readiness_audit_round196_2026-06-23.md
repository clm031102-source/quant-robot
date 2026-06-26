# CN Stock Tradeability Data Readiness Audit - Round196

- Date: 2026-06-23
- Scope: CN stock cross-sectional factor mining
- Stage: process/data-readiness optimization, not factor discovery
- New factors mined: 0
- New promotable factors: 0

## Why This Round Exists

Round195 showed that direct factor generation must stay blocked until the A-share tradeability controls are backed by usable data. This round audited whether the local processed data can support realistic filters before more alpha mining.

The objective is to prevent another blind parameter sweep where signals are later invalidated by limit-up/limit-down, suspension, ST, new listing, delisting, or board-permission constraints.

## Data Audited

- Data roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
  - `data/processed/cn_stock_metadata`
- Bars files: 13
- Bars rows: 11,450,245
- Bars assets: 5,774
- Bars date range: 2015-01-05 to 2026-06-15
- Expected long-cycle window: 2015-01-01 to 2025-12-31
- Coverage result: covered
- Stock basic files: 1
- Stock basic rows: 5,529
- Stock basic assets: 5,529

## Control Results

| Control | Status | Direct-mining usable | Reason |
|---|---|---:|---|
| limit_up_down_filter | proxy_only | false | OHLCV can infer limit-like behavior, but no official up_limit/down_limit field is present. |
| suspension_filter | proxy_only | false | Missing asset/date rows can proxy non-trading days, but cannot separate suspension from universe gaps. |
| st_flag_filter | blocked_missing_official_history | false | Current stock_basic names are only a snapshot proxy, not historical ST timing. |
| new_listing_age_filter | ready | true | stock_basic list_date is present. |
| delisting_risk_filter | blocked_missing_official_history | false | Current/active stock_basic snapshot is not a PIT delisting universe. |
| board_permission_filter | ready | true | exchange/stock_market fields are present. |

## Decision

Direct factor generation remains blocked.

Ready controls: 2 of 6.

Blocking controls: 4 of 6.

Missing official feeds:

- `tushare_stk_limit_or_limit_list`
- `tushare_suspend_d`
- `tushare_namechange_or_historical_st_flag`
- `tushare_stock_basic_all_status_or_delist_feed`

Allowed next work modes:

- official tradeability feed backfill
- tradeability mask implementation
- candidate preregistration without profit claims

## Next Direction

`round197_backfill_official_tradeability_feeds_before_direct_factor_generation`

The next productive work is to implement/backfill official tradeability feeds and produce a reusable asset-date tradeability mask. Direct factor mining should not resume until the mask can distinguish:

- tradable versus limit-blocked entries/exits
- official suspension versus missing coverage
- historical ST windows
- active/listed/paused/delisted point-in-time universe membership

## Practical Conclusion

The project now has enough local bar history for long-cycle CN stock testing, but it still does not have enough official tradeability state to trust newly mined CN stock factors. Any result mined before this closeout would still be exposed to execution infeasibility and survivorship/availability bias.
