# CN Stock External Macro Northbound Credit Data Feed Audit Round166

Date: 2026-06-23

## Scope

Round166 audits whether the project can move away from repeated price/volume/calendar formulas into more orthogonal CN-stock information sources:

- northbound and Stock Connect participation;
- margin financing and securities lending;
- index location and market valuation state;
- macro liquidity and rate state.

This is a data-feed audit, not a factor backtest and not promotion evidence.

## Sources

- Local startup gate source: `docs/research/cn_stock_round163_165_three_round_review_2026-06-23.md`.
- Local endpoint smoke: `data/reports/round166_external_macro_northbound_credit_endpoint_smoke_20260623/endpoint_smoke.json`.
- Tushare official permission/reference page: `https://tushare.pro/document/1?doc_id=108`.

The Tushare official page lists relevant APIs including `margin`, `margin_detail`, `hk_hold`, `index_daily`, `index_dailybasic`, `shibor`, and `shibor_lpr`, with different history starts, update times, and permission requirements. This matters because PIT alignment and endpoint refresh time are part of the alpha definition.

## Endpoint Smoke

The live smoke used the local `TUSHARE_TOKEN` through the project secret loader. The token was not written to command output or reports.

| API | Purpose | Smoke rows | Columns observed | Status |
|---|---|---:|---|---|
| `margin` | exchange-level margin financing and lending summary | 3 | `trade_date`, `exchange_id`, `rzye`, `rzmre`, `rqye`, `rzrqye` | ok |
| `margin_detail` | stock-level margin financing and lending detail | 4,283 | `trade_date`, `ts_code`, `rzye`, `rqye`, `rzmre`, `rqyl`, `rzrqye` | ok |
| `hk_hold` | Stock Connect holding detail | 4,200 | `trade_date`, `ts_code`, `vol`, `ratio`, `exchange` | ok |
| `hsgt_top10` | Stock Connect top traded names | 20 | `trade_date`, `ts_code`, `amount`, `net_amount`, `buy`, `sell` | ok |
| `moneyflow_hsgt` | aggregate northbound/southbound flow | 1 | `hgt`, `sgt`, `north_money`, `south_money` | ok |
| `index_daily` | index price/location state | 5 | `ts_code`, `trade_date`, `close`, `pct_chg`, `amount` | ok |
| `index_dailybasic` | index valuation and turnover state | 12 | `ts_code`, `trade_date`, `turnover_rate`, `pe`, `pe_ttm`, `pb` | ok |
| `shibor` | interbank liquidity/rate state | 5 | `date`, `on`, `1w`, `1m`, `3m`, `1y` | ok |
| `shibor_lpr` | policy loan benchmark state | 1 | `date`, `1y`, `5y` | ok |

Summary: 9 probes, 9 callable, 9 nonempty, 0 endpoint errors.

## Local Processed Data Gap

The local processed/config scan found no existing processed or configured datasets for:

- `hsgt`;
- `northbound`;
- `margin`;
- `credit`;
- `macro`;
- `shibor`;
- `lpr`;
- `index_dailybasic`;
- `hk_hold`.

This means the project has API access but not yet a research-ready processed data layer for this family.

## PIT And Alignment Risks

The audit blocks direct factor mining until these risks are handled:

- `margin` and `margin_detail` are reported after the trading day and must be lagged before same-day signal use.
- `hk_hold` is next-trading-day style holding evidence and must not be used on the trade date without an availability lag.
- `hsgt_top10` is top-list limited, so coverage is sparse and biased toward active names.
- `moneyflow_hsgt` is aggregate market flow, not a stock-level direct signal; it should be regime state or interaction input.
- `index_daily` and `index_dailybasic` are index-level state variables, not stock-level alphas by themselves.
- `shibor` and `shibor_lpr` are macro time series; daily forward-fill and release-time lag must be explicit.
- All external series must be mapped to CN trading dates and must survive signal-window regime coverage checks.

## Decision

Proceed with ingestion design before factor formulas.

Allowed next action:

- `round167_external_feed_ingestion_design_for_northbound_margin_macro`

Blocked actions:

- direct northbound factor mining from endpoint smoke;
- direct margin factor mining without availability lag and stock-universe coverage checks;
- using `hsgt_top10` top-list names as a broad cross-sectional factor;
- treating aggregate `moneyflow_hsgt`, `shibor`, or `index_dailybasic` as a standalone stock-ranking factor;
- portfolio grids before processed data, PIT labels, residual controls, and coverage audits exist.

## Candidate Family Seeds After Ingestion

Only after ingestion and PIT alignment:

- `northbound_holding_change_residual_quality`: stock-level changes in Stock Connect ownership, neutralized by size/liquidity/industry.
- `northbound_top10_flow_exhaustion`: top traded northbound names as a sparse event factor, not broad daily ranking.
- `margin_balance_crowding_reversal`: stock-level margin balance and purchase pressure as crowding/reversal input.
- `margin_short_lending_relief`: securities lending balance/volume as stress or squeeze state.
- `index_location_value_liquidity_interaction`: index valuation/location state conditioning stock residual value/liquidity signals.
- `credit_liquidity_regime_interaction`: SHIBOR/LPR state conditioning reversal, volatility, or liquidity premia.

No candidate is promotable from this audit.

