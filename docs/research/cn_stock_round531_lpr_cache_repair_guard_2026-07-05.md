# CN Stock Round531 LPR Cache Repair Guard

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 28 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, and did not touch final holdout. It hardened LPR cache handling and documented the source-repair path for `external_macro_rates`.

## Round Objective

Round528 and Round529 kept `external_macro_rates` blocked because `lpr_1y` and `lpr_5y` had 0 non-null rows. Round530 removed the external-feed join-smoke performance blocker, leaving LPR coverage as the main macro-source repair item.

Round531 focused on the first safe repair step:

- prevent empty LPR cache files from being silently reused;
- expose an explicit CLI cache path for future report-only LPR refresh attempts;
- keep all LPR-dependent factors blocked until non-missing coverage is proven.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 05:01 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Evidence Read

Code and tests reviewed:

- `src/quant_robot/data/ingest/tushare_external_feeds.py`
- `scripts/run_tushare_external_feed_ingest.py`
- `src/quant_robot/ops/external_feed_coverage_audit.py`
- `src/quant_robot/ops/external_feed_backfill_plan.py`
- `tests/unit/test_tushare_external_feed_ingest.py`
- `tests/unit/test_tushare_external_feed_ingest_cli.py`
- `tests/unit/test_external_feed_coverage_audit.py`

Historical evidence reviewed:

- `docs/research/cn_stock_external_feed_processed_ingestion_implementation_round169_2026-06-23.md`
- `docs/research/cn_stock_external_feed_eighteenth_monthly_shard_round190_2026-06-23.md`
- `docs/research/cn_stock_china_market_regime_control_gate_round205_2026-06-23.md`
- `docs/research/cn_stock_round528_external_feed_rotation_source_audit_2026-07-05.md`
- `docs/research/cn_stock_round529_external_feed_family_review_2026-07-05.md`
- `docs/research/cn_stock_round530_external_feed_join_smoke_optimization_2026-07-05.md`

## Root Cause Hypothesis

The ingestion engine already supports `shibor_lpr` and joins LPR to daily SHIBOR with a backward as-of merge. Unit tests prove that when the adapter returns LPR rows, processed `external_macro_rates` contains non-null `lpr_1y` and `lpr_5y`.

The long-cycle processed root has 340 SHIBOR-complete macro rows and 0 non-null LPR rows. That points to source acquisition or cache reuse, not to missing processed columns or a coverage-audit bug.

Most likely failure mode:

- `shibor_lpr` was unavailable, rate-limited, or returned empty during earlier shards;
- an empty or all-missing `external_lpr_cache.json` could then be reused by later shards;
- SHIBOR continued to accumulate while LPR remained fully missing.

## Implementation

Changed:

- `src/quant_robot/data/ingest/tushare_external_feeds.py`
- `scripts/run_tushare_external_feed_ingest.py`
- `tests/unit/test_tushare_external_feed_ingest.py`
- `tests/unit/test_tushare_external_feed_ingest_cli.py`

Key implementation points:

- Added `_has_non_missing_lpr_values`.
- Existing LPR cache files are now accepted only when they contain at least one row with non-missing `date`, `lpr_1y`, and `lpr_5y`.
- Empty or all-missing LPR cache files emit `shibor_lpr` progress status `cache_refresh` with warning `lpr_cache_empty_or_missing_values`, then retry the endpoint.
- The CLI now exposes `--lpr-cache-path` and forwards it to `run_tushare_external_feed_ingest`.

## Test-First Evidence

New failing tests were added before implementation:

- `test_empty_lpr_cache_is_refreshed_instead_of_reused`
- `test_cli_passes_explicit_lpr_cache_path`

Observed red evidence:

- The empty-cache test initially failed because `adapter.lpr_calls` stayed `0`.
- The CLI test initially failed with argparse error `unrecognized arguments: --lpr-cache-path`.

Focused green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_tushare_external_feed_ingest tests.unit.test_tushare_external_feed_ingest_cli tests.unit.test_external_feed_coverage_audit tests.unit.test_external_feed_coverage_audit_cli
```

Result:

- 17 tests passed.

Additional local verification:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --help
.\.venv\Scripts\python.exe -m py_compile src\quant_robot\data\ingest\tushare_external_feeds.py scripts\run_tushare_external_feed_ingest.py
```

The help output includes `--lpr-cache-path`; compile exited `0`.

## Repair Path

Do not run these commands on a same-day provider-budget block. Use them only when provider use is allowed and the user intentionally wants a source-repair attempt.

Step 1: report-only LPR cache refresh with an isolated cache path.

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-07-01 --end-date 2024-07-01 --output-dir data\reports\round532_external_feed_lpr_report_only_20240701_<YYYYMMDD> --lpr-cache-path data\reports\round532_external_lpr_cache_refresh_<YYYYMMDD>\external_lpr_cache.json --progress-jsonl data\reports\round532_external_feed_lpr_report_only_20240701_<YYYYMMDD>\progress.jsonl
```

Pass criteria before any processed write:

- progress JSONL contains `shibor_lpr` status `done`;
- `external_lpr_cache.json` exists under the isolated cache path;
- cache rows are non-empty;
- at least one row has non-missing `lpr_1y` and `lpr_5y`;
- report-only `feed_quality.external_macro_rates.status` is not failed by LPR missingness;
- no `data/processed` output is written by this step.

Step 2: only after Step 1 passes, choose one repair path.

Allowed repair paths:

- rebuild a new processed external-feed root using `--execute-write-processed` and the validated LPR cache path;
- or implement an offline macro-rate repair script that applies the validated LPR cache to existing `external_macro_rates` partitions with a fresh processed output root.

Blocked repair paths:

- do not overwrite the existing long-cycle processed root in place;
- do not treat SHIBOR-only coverage as LPR coverage;
- do not lower the coverage-audit threshold to pass LPR;
- do not run LPR factors, portfolio grids, promotion gates, or final-holdout reads before coverage audit passes.

Step 3: rerun coverage audit on the repaired processed root.

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root <REPAIRED_EXTERNAL_FEED_PROCESSED_ROOT> --output-dir data\reports\round532_external_feed_lpr_repair_coverage_audit_<YYYYMMDD> --market CN
```

Required result:

- `external_macro_rates.status` is `pass`;
- `lpr_non_null_ratio >= 0.8`;
- `lpr_1y_non_null_rows > 0`;
- `lpr_5y_non_null_rows > 0`;
- `external_feed_ic_or_portfolio_allowed` may become true only as a source audit field, not as alpha evidence.

## Decision

LPR-dependent factors remain blocked.

Round531 only repairs a source-ingestion guard and prepares the cache-refresh path. It does not produce non-missing LPR coverage, does not change `external_macro_rates` processed data, and does not allow macro/liquidity factor testing.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run external-feed portfolio grids or promotion gates from coverage audit or join smoke.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
