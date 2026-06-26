# CN Stock External Feed Ingestion Design Round167

Date: 2026-06-23

## Goal

Convert the Round166 endpoint audit into a minimal, point-in-time safe ingestion plan for external CN-stock research feeds before any northbound, margin, index-state, or macro-liquidity factor is generated.

## Source Evidence

- Round166 audit: `docs/research/cn_stock_external_macro_northbound_credit_data_feed_audit_round166_2026-06-23.md`.
- Endpoint smoke: `data/reports/round166_external_macro_northbound_credit_endpoint_smoke_20260623/endpoint_smoke.json`.
- Startup gate now blocks direct factor mining from endpoint smoke.

## Minimal Feed Set

| Feed | Tushare API | Grain | Why Include | PIT Availability Rule |
|---|---|---|---|---|
| Margin detail | `margin_detail` | stock-date | Stock-level financing/lending pressure, crowding, stress | Available no earlier than next trading day after `trade_date` |
| Stock Connect holdings | `hk_hold` | stock-date | Northbound ownership participation and holding change | Available no earlier than next trading day after `trade_date` |
| Aggregate Stock Connect flow | `moneyflow_hsgt` | market-date | Market-wide northbound/southbound flow regime | Available no earlier than next trading day after `trade_date` |
| Index prices | `index_daily` | index-date | Index location, drawdown, trend, volatility state | Available after index close; use next trading day for stock signal |
| Index daily basic | `index_dailybasic` | index-date | Index valuation, turnover, float MV state | Available after daily update; use next trading day for stock signal |
| Rates/liquidity | `shibor`, `shibor_lpr` | macro-date | Credit/liquidity cycle state | Use next CN trading day after release date unless release time is explicitly modeled |

Excluded from broad factor matrix:

- `hsgt_top10`: keep as a sparse event feed only. It is not a broad cross-sectional ranking universe.
- `margin`: keep as market-level summary, not stock-level alpha, unless used as a regime control.

## Processed Layout

Use project-style partitioning under a future local data root:

- `processed/external_margin_detail/frequency=1d/market=CN/year=<YYYY>/part.parquet`
- `processed/external_hk_hold/frequency=1d/market=CN/year=<YYYY>/part.parquet`
- `processed/external_hsgt_flow/frequency=1d/market=CN/year=<YYYY>/part.parquet`
- `processed/external_index_state/frequency=1d/market=CN/year=<YYYY>/part.parquet`
- `processed/external_macro_rates/frequency=1d/market=CN/year=<YYYY>/part.parquet`

Generated reports and trial outputs stay under `data/reports`. Raw and processed data remain out of Git.

## Canonical Columns

`external_margin_detail`:

- `symbol`
- `date`
- `available_date`
- `rzye`
- `rqye`
- `rzmre`
- `rqyl`
- `rzche`
- `rqchl`
- `rqmcl`
- `rzrqye`

`external_hk_hold`:

- `symbol`
- `date`
- `available_date`
- `hold_vol`
- `hold_ratio`
- `exchange`

`external_hsgt_flow`:

- `date`
- `available_date`
- `hgt`
- `sgt`
- `north_money`
- `south_money`

`external_index_state`:

- `index_symbol`
- `date`
- `available_date`
- `close`
- `pct_chg`
- `amount`
- `turnover_rate`
- `turnover_rate_f`
- `pe`
- `pe_ttm`
- `pb`

`external_macro_rates`:

- `date`
- `available_date`
- `shibor_on`
- `shibor_1w`
- `shibor_1m`
- `shibor_3m`
- `shibor_1y`
- `lpr_1y`
- `lpr_5y`

## Quality Gates

Before factor generation, each feed must report:

- row count;
- date min/max;
- unique symbol or index count where applicable;
- duplicate key count;
- missing required field count;
- date-to-CN-trading-calendar alignment;
- `available_date > date` for feeds that are not safe for same-day use;
- coverage by year;
- final-holdout exclusion status.

Hard blockers:

- duplicate `(symbol, date)` keys after normalization;
- missing or non-monotonic `available_date`;
- direct use of `date` instead of `available_date` for signal joins;
- sparse top-list feed represented as full-universe cross-section;
- endpoint smoke counted as processed coverage.

## First Implementation Slice

The first implementation should be deliberately small:

1. Create mapping functions for the five canonical processed frames.
2. Add fixture-based unit tests for each mapping and PIT lag rule.
3. Add a CLI that can run a date-window smoke and writes only reports by default.
4. Add an `--execute-write-processed` flag later, after the report-only smoke proves schema and coverage.

This avoids immediately launching a large backfill before schema, lag, and coverage rules are test-covered.

## Factor Seeds After Ingestion

Only after processed feeds pass quality gates:

- `northbound_holding_change_residual_quality`
- `northbound_aggregate_flow_regime_interaction`
- `margin_balance_crowding_reversal`
- `margin_financing_acceleration_exhaustion`
- `index_location_value_liquidity_interaction`
- `credit_liquidity_regime_reversal`

No portfolio grid is allowed until the factor matrix uses `available_date` joins and passes residual IC/redundancy checks.

## Decision

Proceed to:

- `round168_external_feed_report_only_ingestion_smoke`

Do not start factor mining from these external feeds until the report-only ingestion smoke passes.

