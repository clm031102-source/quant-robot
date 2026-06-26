# CN Stock External Feed Processed Ingestion Implementation Round169

Date: 2026-06-23

## Scope

Round169 converted the Round167/168 external macro, northbound, and credit-feed ingestion plan into reusable project code. This round produced no factor and no profitability claim.

- Machine/task: `office_desktop` / `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stock research
- Safety: research-to-review only. No broker connection, no account reads, no orders, no live trading.

## What Changed

- Added `src/quant_robot/data/ingest/tushare_external_feeds.py`.
- Added `scripts/run_tushare_external_feed_ingest.py`.
- Added Tushare adapter methods for `margin_detail`, `hk_hold`, `moneyflow_hsgt`, `index_daily`, `index_dailybasic`, `shibor`, and `shibor_lpr`.
- Added unit and CLI tests for report-only default, explicit processed writes, `available_date` lag, LPR cache, missing next-trading-day failure, and HK-symbol filtering.

The default CLI mode writes only a report. Processed datasets require `--execute-write-processed`.

## Canonical Feeds

| Feed | Status | Key PIT Rule |
|---|---|---|
| `external_margin_detail` | implemented | `available_date` is next CN trading day after `date` |
| `external_hk_hold` | implemented | non-CN suffixes are dropped; `available_date` is next CN trading day |
| `external_hsgt_flow` | implemented | aggregate regime feed only; not a standalone stock rank |
| `external_index_state` | implemented | index close/daily-basic are lagged to next trading day |
| `external_macro_rates` | implemented with LPR warning path | SHIBOR is date-looped; LPR is cached/throttled and may warn when rate-limited |

## Live Report-Only Smoke

Command:

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-12-25 --end-date 2025-12-31 --output-dir data\reports\round169_external_feed_processed_ingestion_implementation_smoke_20260623
```

Result:

| Feed | Status | Rows | Entities | Duplicate Keys | Lag Violations | Missing Available Date | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| `external_margin_detail` | pass | 21,396 | 4,284 | 0 | 0 | 0 | `rqye` and `rzrqye` each missing 15 rows |
| `external_hk_hold` | pass | 3,325 | 3,325 | 0 | 0 | 0 | dropped 2,625 non-CN symbols such as HK codes |
| `external_hsgt_flow` | pass | 3 | n/a | 0 | 0 | 0 | aggregate flow only |
| `external_index_state` | pass | 5 | 1 | 0 | 0 | 0 | default index `000001.SH` |
| `external_macro_rates` | warn | 5 | n/a | 0 | 0 | 0 | LPR unavailable/rate-limited; SHIBOR present |

Summary: 5 feeds, 4 pass, 1 warn, 0 fail.

## Important Discovery

`hk_hold` can include HK symbols such as `00001.HK`. For this CN-stock factor project, those rows are filtered before `asset_id` mapping and the dropped count is recorded. Without this filter, the ingestion would either fail or contaminate the CN A-share research universe.

## Verification

- `python -m unittest tests.unit.test_tushare_external_feed_ingest tests.unit.test_tushare_external_feed_ingest_cli tests.unit.test_tushare_factor_inputs_ingest tests.unit.test_tushare_moneyflow_inputs_ingest tests.unit.test_tushare_mapping`: 38 tests OK.
- `python -m py_compile src\quant_robot\data\ingest\tushare_external_feeds.py scripts\run_tushare_external_feed_ingest.py src\quant_robot\data\adapters\tushare_adapter.py`: exit 0.
- Startup gate remained cleared for `office_desktop / factor_validation`.
- `git ls-files data/raw data/processed data/reports`: 0 tracked paths.

## Decision

Round169 is an ingestion-engineering success, not alpha evidence.

Proceed to:

`round170_external_feed_processed_write_smoke_and_factor_seed_preregistration`

Round170 must:

- run a small explicit processed-write smoke under local ignored data paths;
- audit processed coverage and `available_date` joins;
- preregister only a small external-feed factor seed set;
- keep all promotion blocked until IC, redundancy, cost/capacity, walk-forward, and regime gates pass.
