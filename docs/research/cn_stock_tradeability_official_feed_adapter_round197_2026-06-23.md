# CN Stock Tradeability Official Feed Adapter - Round197

Date: 2026-06-23

## Objective

Optimize the CN-stock factor-mining gate before resuming direct alpha mining. The main risk from prior rounds was that A-share tradeability controls were inferred from OHLCV proxies instead of official point-in-time feeds, making limit-up/down, suspension, ST, and delisting filters unreliable.

## Changes

- Added official Tushare tradeability feed ingestion for:
  - `stk_limit` as `processed/tradeability_stk_limit`
  - `suspend_d` as `processed/tradeability_suspension`
  - `namechange` as `processed/tradeability_namechange`
  - `stock_basic` L/P/D snapshots as `metadata/tushare_stock_basic`
- Fixed the live `suspend_d` contract to use `trade_date`; using `suspend_date` returned unrelated historical rows.
- Normalized real `suspend_d` columns `suspend_timing` and `suspend_type`.
- Treated missing paused stock-basic status `P` as an optional warning when live `L` and delisted `D` are present.
- Deduplicated duplicate suspension and namechange events before quality checks.
- Updated tradeability data-readiness audit to recognize standalone official processed datasets, not only fields embedded in bars.

## Verification

- Unit and integration-adjacent tests:
  - `python -m unittest tests.unit.test_tushare_tradeability_feeds_ingest`
  - `python -m unittest tests.unit.test_cn_stock_tradeability_data_readiness_audit`
  - Broader gate suite later covered 62 related tests before final verification.
- Live Tushare report-only smoke, 2024-01-02 to 2024-01-03:
  - `fail_count`: 0
  - `stk_limit`: 13,434 rows, 6,718 entities
  - `suspend_d`: 33 rows, 17 entities
  - `stock_basic`: L/D present, P missing as optional warning
- Live Tushare report-only smoke, 2024-01-02 to 2024-01-31:
  - `fail_count`: 0
  - `stk_limit`: 148,035 rows, 6,741 entities
  - `suspend_d`: 300 rows, 29 entities
  - `namechange`: 2 rows, 2 ST-name rows
  - `stock_basic`: 5,855 entities, 331 delist-date rows
- Processed smoke audit with January official feeds plus existing long-cycle bars:
  - `status`: `tradeability_data_ready`
  - ready controls: 6/6
  - blocking controls: 0
  - direct factor generation allowed for the smoke scope: true

## Current Production Data Status

The default long-cycle CN stock data roots still do not include official tradeability feeds:

- `tradeability_stk_limit`: 0 files
- `tradeability_suspension`: 0 files
- `tradeability_namechange`: 0 files
- Direct factor generation on the full default scope remains blocked.

## Decision

Do not resume unrestricted direct CN-stock factor mining yet. The next useful work is a controlled long-cycle official tradeability backfill, then tradeability-mask integration into factor matrix and portfolio simulation. Candidate preregistration may continue, but no profit/promotion claim should be made without these masks.

Next direction: `round198_long_cycle_official_tradeability_backfill_and_mask_integration`
