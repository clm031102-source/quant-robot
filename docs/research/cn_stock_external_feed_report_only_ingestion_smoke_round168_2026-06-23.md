# CN Stock External Feed Report-Only Ingestion Smoke Round168

Date: 2026-06-23

## Scope

Round168 executes the first report-only ingestion smoke from the Round167 design. It validates canonical schemas, duplicate keys, and `available_date` lag behavior for a small live Tushare window without writing processed data.

Output pack:

- `data/reports/round168_external_feed_report_only_ingestion_smoke_20260623/external_feed_report_only_ingestion_smoke.json`

## Smoke Window

- Start: 2025-12-25
- End: 2025-12-31
- CN trading dates: 2025-12-25, 2025-12-26, 2025-12-29, 2025-12-30, 2025-12-31
- Processed writes: false
- Token written to output: false

## Results

| Feed | Status | Rows | Date Range | Entities | Duplicate Keys | Lag Violations | Missing Fields |
|---|---|---:|---|---:|---:|---:|---|
| `external_margin_detail` | pass | 21,396 | 2025-12-25 to 2025-12-31 | 4,284 | 0 | 0 | `rqye`: 15, `rzrqye`: 15 |
| `external_hk_hold` | pass | 5,950 | 2025-12-29 to 2025-12-31 | 4,202 | 0 | 0 | none |
| `external_hsgt_flow` | pass | 3 | 2025-12-29 to 2025-12-31 | n/a | 0 | 0 | none |
| `external_index_state` | pass | 5 | 2025-12-25 to 2025-12-31 | 1 | 0 | 0 | none |
| `external_macro_rates` | warn | 5 | 2025-12-25 to 2025-12-31 | n/a | 0 | 0 | `lpr_1y`: 5, `lpr_5y`: 5 |

Summary:

- feed count: 5
- pass count: 4
- warn count: 1
- fail count: 0

## Root-Cause Notes

Two endpoint behavior issues were discovered during the smoke:

1. `trade_cal` briefly returned an unusable frame during the first run, then returned normal `cal_date` data with the same parameters. The smoke should use retry and column validation at the provider boundary.
2. `shibor` did not return rows for the tested `start_date`/`end_date` query shape, but returned valid rows when queried by `date`.
3. `shibor_lpr` is much more rate-limited than the other endpoints and hit a frequency limit during repeated smoke attempts. LPR ingestion must be cached and throttled separately.

These are ingestion-engineering issues, not factor evidence.

## Decision

Proceed to production-style ingestion implementation, but only with strict safeguards.

Allowed next action:

- `round169_external_feed_processed_ingestion_implementation_with_lpr_throttle`

Required before any factor mining:

- canonical mapping functions with unit tests;
- retry and schema validation for provider boundary responses;
- `available_date` derived from CN trading calendar and used for all signal joins;
- LPR-specific throttle/cache handling;
- field-level missingness report for margin detail;
- report-only mode remains default;
- processed writes require an explicit execute flag and must remain out of Git.

Blocked actions:

- direct factor generation from Round168 sample files;
- direct portfolio grids from endpoint smoke or report-only smoke;
- macro rate factors using same-day release assumptions;
- Stock Connect holding factors without next-trading-day availability lag.

