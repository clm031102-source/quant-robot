# Phase 1.5 Real Data, Tushare, And TradingView Design

## 1. Goal

Phase 1.5 turns the existing offline fixture framework into a real-data research foundation while preserving the phase-one no-live-trading boundary.

The goal is to support:

- Tushare as the primary A-share daily data source.
- AKShare as an A-share fallback and cross-check source.
- yfinance as the initial Hong Kong and US daily data source.
- ccxt as the initial crypto daily data source.
- TradingView as a chart verification, CSV import, Pine Script prototyping, and future webhook signal source.

Phase 1.5 remains research-only. It does not connect to broker accounts, place orders, store broker secrets, or automate live trading.

## 2. Recommended Path

Use a three-ring design:

```text
Ring 1: Offline-testable core
  config, token loading, schema mapping, quality reports, CSV parsing, adapter contracts

Ring 2: Optional live data adapters
  Tushare, AKShare, yfinance, ccxt wrappers with runtime optional imports

Ring 3: Research execution
  ingest scripts, Parquet persistence, factor/research/backtest pipeline from real data
```

This path is better than starting with direct live downloads because it lets the framework be tested without paid accounts, network access, or optional packages. Real credentials only activate the final source-specific call layer.

## 3. Tushare Role

Tushare is the preferred A-share source once the user buys or obtains sufficient points. The 2000-point tier is a practical target because it unlocks the important A-share research endpoints and increases request capacity compared with the free baseline.

Phase 1.5 should target these Tushare endpoints first:

- `trade_cal`: exchange trading calendar.
- `stock_basic`: A-share security master data.
- `daily`: unadjusted daily OHLCV.
- `adj_factor`: adjustment factors.
- `daily_basic`: turnover, market value, PE, PB, and other daily indicators.

The system should not depend on Tushare for Hong Kong or US data in Phase 1.5 because those permissions are often separate from the A-share points tier. Hong Kong and US can start with yfinance and later be upgraded if the user chooses.

Official references used for planning:

- Tushare points and frequency table: https://tushare.pro/document/1?doc_id=290
- Tushare API permission notes: https://tushare.pro/document/1?doc_id=108
- Tushare efficient data extraction guidance: https://tushare.pro/document/1?doc_id=230
- Tushare adjustment factor endpoint: https://tushare.pro/document/2?doc_id=28

## 4. TradingView Role

TradingView should not be treated as the research system's historical data warehouse. It should be used as:

- A chart-side verification surface for signals and factor behavior.
- A CSV import source for manual spot checks.
- A Pine Script prototype target for visually checking ideas.
- A future webhook signal source for paper trading only.

Phase 1.5 implements TradingView CSV import and Pine template generation boundaries. Webhook receiving is designed but not activated until the paper-trading phase.

Official references used for planning:

- TradingView webhook alerts: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- TradingView alerts overview: https://www.tradingview.com/support/solutions/43000520149-introduction-to-tradingview-alerts/
- TradingView chart data export: https://www.tradingview.com/support/solutions/43000537255-how-can-i-export-chart-data

## 5. Data Ingestion Architecture

The ingestion layer has this flow:

```text
source adapter
  -> raw dataframe
  -> raw parquet or raw csv archive
  -> source-specific mapper
  -> canonical normalized OHLCV
  -> data quality report
  -> processed parquet
```

The source adapter is allowed to know provider-specific names such as `ts_code`, `trade_date`, or TradingView CSV headings. No factor, research, or backtest code is allowed to know provider-specific field names.

## 6. Token And Secret Handling

Secrets must be loaded from environment variables or an ignored `.env` file.

Rules:

- `TUSHARE_TOKEN` is never committed.
- `.env.example` documents expected variables with blank values.
- Token loading lives in `src/quant_robot/config/secrets.py`.
- If a required token is missing, the adapter raises a clear runtime error.
- Tests use fake clients and never require real secrets.

## 7. Tushare Extraction Strategy

Support two modes:

1. Small-universe mode:
   - Pull by `ts_code` and date range.
   - Useful for debugging and early research.

2. Full-market mode:
   - Pull by `trade_date`.
   - Use `trade_cal` to find open days.
   - This follows Tushare's efficient extraction guidance because full-market daily pulls by date avoid thousands of stock-level loops.

Both modes must support:

- Retry with bounded attempts.
- Request pacing.
- Incremental resume based on existing raw partitions.
- Failure logging.
- Deterministic storage paths.

## 8. Canonical A-Share Mapping

Tushare daily fields map into canonical OHLCV:

```text
ts_code -> source_symbol
trade_date -> date
open -> open
high -> high
low -> low
close -> close
vol -> volume
amount -> amount
```

Additional notes:

- Tushare `vol` is usually reported in hands for A-shares; canonical `volume` should be shares after multiplying by 100 when source metadata confirms that unit.
- Tushare `amount` is usually reported in thousand yuan; canonical `amount` should be CNY after multiplying by 1000 when source metadata confirms that unit.
- Adjustment factors are joined by `(ts_code, trade_date)`.
- The first Phase 1.5 adjusted close can be `close * adj_factor / latest_adj_factor` for forward-adjusted research mode, with metadata recording the adjustment method.

## 9. Data Quality Reports

Quality reports should be generated after normalization:

- Required column presence.
- Duplicate bars.
- OHLC consistency.
- Negative price or volume checks.
- Missing trading dates per asset.
- Suspicious zero-volume rows.
- Adjustment factor missing ratio.
- Coverage by market, asset, and date.

The first implementation can output JSON and CSV. Later versions can add charts.

## 10. TradingView CSV Import

TradingView CSV import should be intentionally manual:

```text
user exports chart data from TradingView
  -> scripts/import_tradingview_csv.py
  -> parsed source dataframe
  -> canonical normalized OHLCV
  -> comparison report against local source data
```

This is for validation, not bulk data acquisition.

## 11. Pine Script Templates

The first Pine template should cover:

- Plotting moving momentum or reversal signals.
- Marking long/flat conditions.
- Emitting JSON-shaped alert messages for future paper-trading use.

Pine templates are not production strategies. They are visual inspection tools.

## 12. Phase 1.5 Completion Standard

Phase 1.5 is complete when:

- Tushare token loading is implemented safely.
- Tushare adapter can be tested with fake clients without installing Tushare.
- Tushare daily, adjustment factor, stock basic, and trade calendar mapping contracts are implemented.
- TradingView CSV import is implemented and tested.
- Data quality report generation is implemented and tested.
- Ingest CLI can run offline fixtures and can call live adapters when dependencies and credentials are present.
- Parquet storage is fully enabled when `pyarrow` or `fastparquet` is installed.
- Existing factor/research/backtest pipeline can consume real normalized bars.
- No live trading, broker login, or automatic order placement code exists.
