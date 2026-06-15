# Phase 2.8 Promotion Operations Design

## Objective

Advance the project from a one-shot Phase 2.7 promotion gate to a local Phase 2.8 operations layer, then prepare the next two foundations in order: Tushare CN ETF ingestion and more realistic paper execution constraints.

## Scope

Phase 2.8 stays research-only. It does not add broker adapters, account reads, order placement, live routing, or investment advice. It consumes local reports and processed bars only.

## Design

The operations layer reads `promotion_report.json`, optional `provider_status.json`, and optional ETF data-quality reports. It builds a compact console payload with candidate counts, the top candidate, live-review blockers, duplicate clusters, evidence status, and next actions. The GUI exposes this through `/api/promotion/ops`.

The CN ETF provider path extends the existing Tushare adapter instead of adding a new provider abstraction. `CN` keeps using `daily`; `CN_ETF` uses `fund_daily`. The existing ingest pipeline accepts `market="CN_ETF"` and writes processed bars under `market=CN_ETF`.

The execution-realism layer keeps paper simulation local and deterministic. If optional bar columns such as `suspended`, `limit_up`, or `limit_down` are present, the simulator blocks fills and records execution events. Zero-volume execution bars are also blocked.

## Testing

Tests cover the operations summary, local API wiring, CN ETF Tushare adapter routing, provider status, CN ETF ingest partitions, and paper execution-block events. The old CN ingest manifest keys remain compatible.
