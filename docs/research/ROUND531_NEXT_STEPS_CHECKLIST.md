# Round531 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 28 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota state: Round526 safe cache-CLI dry-run with required machines and notes blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest Round530 work: full-window external-feed join smoke optimized and verified locally without provider calls.
- Latest Round531 work: LPR cache guard added and external-feed ingest CLI now exposes `--lpr-cache-path`.

## Next Best Target

If still on 2026-07-05, do not run provider-backed analyst cache and do not repeat the same quota dry-run without new cross-machine quota evidence.

The next useful work is one of:

- produce or import real quota packs from `highspec_desktop` and `laptop`;
- wait until the local quota date changes, then run one actual-date analyst preflight with required-machine constraints;
- after successful April analyst cache, run the frozen January-April prescreen exactly once;
- if provider use is allowed, run a report-only LPR cache refresh with an explicit isolated cache path;
- if provider use is not allowed, draft an offline macro-rate LPR repair script design that consumes a validated LPR cache later.

## Before Any Command

Run these local gates first:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if any gate has blockers. The CN stock data manifest may return `review_required`; read warnings before continuing.

## Analyst Required-Machine Dry-Run

Run this only after the local quota date changes or after real cross-machine quota evidence is added:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round532_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round532_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round532_required_machine_quota_preflight_<YYYYMMDD> --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=<reason and timestamp if still unavailable>" --quota-pack-machine-note "laptop=<reason and timestamp if still unavailable>" --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

## Frozen Analyst Prescreen

Run this only after April cache actually succeeds. Replace `<APRIL_CACHE_PROCESSED_ROOT>` with the processed output directory from the successful April cache.

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root <APRIL_CACHE_PROCESSED_ROOT> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round532_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Do not add `--include-final-holdout`.

## LPR Cache Refresh Gate

Run this only when provider use is allowed. It is report-only and should not write processed data.

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-07-01 --end-date 2024-07-01 --output-dir data\reports\round532_external_feed_lpr_report_only_20240701_<YYYYMMDD> --lpr-cache-path data\reports\round532_external_lpr_cache_refresh_<YYYYMMDD>\external_lpr_cache.json --progress-jsonl data\reports\round532_external_feed_lpr_report_only_20240701_<YYYYMMDD>\progress.jsonl
```

Stop unless all are true:

- progress JSONL contains `shibor_lpr` status `done`;
- isolated `external_lpr_cache.json` exists;
- cache rows are non-empty;
- at least one row has non-missing `lpr_1y` and `lpr_5y`;
- no processed write was requested;
- no data output is staged for Git.

## LPR Processed Repair Gate

Run only after the LPR cache refresh gate passes.

Allowed:

- rebuild a new external-feed processed root with `--execute-write-processed` and the validated `--lpr-cache-path`;
- or implement an offline macro-rate repair script that reads existing `external_macro_rates`, applies the validated LPR cache by as-of date, and writes a fresh processed root.

Blocked:

- no in-place overwrite of the existing long-cycle processed root;
- no lower LPR coverage threshold;
- no SHIBOR-only substitute for LPR coverage;
- no LPR factor, portfolio grid, promotion gate, or final-holdout read before coverage audit passes.

After repair, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root <REPAIRED_EXTERNAL_FEED_PROCESSED_ROOT> --output-dir data\reports\round532_external_feed_lpr_repair_coverage_audit_<YYYYMMDD> --market CN
```

Required result before any LPR-dependent work:

- `external_macro_rates.status=pass`;
- `lpr_non_null_ratio >= 0.8`;
- `lpr_1y_non_null_rows > 0`;
- `lpr_5y_non_null_rows > 0`.

## Red Lines

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run portfolio grids or promotion gates.
- Do not commit generated `data/` outputs, Parquet/CSV files, logs, tokens, broker credentials, account data, or order data.
- Do not use `--skip-quota-preflight` for normal provider-backed analyst-report fetches.
- Do not use nonlocal `--quota-target-date` for provider-backed cache execution.

## Stop Or Rotate Conditions

- Stop if the analyst cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if required cross-machine quota packs are unavailable.
- Stop if LPR cache refresh does not produce non-missing `lpr_1y` and `lpr_5y`.
- Keep external LPR/macro factors blocked until LPR non-missing coverage is repaired and coverage audit passes.
