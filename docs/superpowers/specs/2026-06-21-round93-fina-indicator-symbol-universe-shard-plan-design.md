# Round93 Fina Indicator Symbol Universe Shard Plan Design

## Goal

Create a deterministic symbol-universe and shard plan for a larger Tushare `fina_indicator` backfill, without starting the full backfill.

## Context

Round92 proved the limited two-symbol long-history path. A full listed-symbol universe can require more than 240,000 symbol-period requests. The next step must define exactly which symbols are in scope, how requests are split into shards, and which per-shard gates must pass before any profitability factor pre-registration.

## Selected Approach

Build a planning-only operation:

- Read explicit symbols, a symbol file, or local `stock_basic` parquet/csv files.
- Normalize and deduplicate Tushare symbols.
- Optionally exclude Beijing Stock Exchange symbols for the first broad backfill shard plan.
- Generate quarterly periods from 2015-03-31 through 2025-12-31.
- Split symbols into deterministic shards by symbol count.
- For each shard, report symbols, periods, request count, first/last symbol, and blockers.
- Write compact JSON and Markdown artifacts.
- Do not call Tushare.
- Do not write raw or processed market data.

## Success Criteria

- Unit tests prove deterministic shard counts and budget blockers.
- CLI tests prove artifacts are written from a symbol file.
- Real local plan is generated from `data/processed/cn_stock_metadata`.
- Startup gate advances only to a first-shard smoke, not a full-universe run.
