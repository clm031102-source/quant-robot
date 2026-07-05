# Round532 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 29 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota state: Round526 safe cache-CLI dry-run with required machines and notes blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest Round531 work: LPR cache guard added and external-feed ingest CLI exposes `--lpr-cache-path`.
- Latest Round532 work: offline external macro LPR repair tool added; no provider calls and no real processed repair run.

## Next Best Target

Round533 is a required review-agent checkpoint. Before further provider calls, factor work, or source repair execution, create two review agents:

- Quant PM reviewer: evaluate analyst quota path, LPR repair path, external-feed hibernation boundary, and whether the next action should consume provider quota.
- Ordinary user reviewer: evaluate whether the current workflow is understandable and hard to misuse, especially around placeholders, cache paths, output roots, and non-Git data.

If still on 2026-07-05, do not run provider-backed analyst cache and do not repeat the same quota dry-run without new cross-machine quota evidence.

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
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round533_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round533_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round533_required_machine_quota_preflight_<YYYYMMDD> --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=<reason and timestamp if still unavailable>" --quota-pack-machine-note "laptop=<reason and timestamp if still unavailable>" --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

## LPR Cache And Offline Repair Gate

Run the cache refresh only when provider use is allowed. It is report-only and should not write processed data:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-07-01 --end-date 2024-07-01 --output-dir data\reports\round533_external_feed_lpr_report_only_20240701_<YYYYMMDD> --lpr-cache-path data\reports\round533_external_lpr_cache_refresh_<YYYYMMDD>\external_lpr_cache.json --progress-jsonl data\reports\round533_external_feed_lpr_report_only_20240701_<YYYYMMDD>\progress.jsonl
```

Only after that cache has non-missing `lpr_1y` and `lpr_5y`, run the offline repair into a fresh processed root:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --lpr-cache-path data\reports\round533_external_lpr_cache_refresh_<YYYYMMDD>\external_lpr_cache.json --output-root data\processed\round533_external_feeds_lpr_repaired_<YYYYMMDD> --report-dir data\reports\round533_external_macro_lpr_repair_<YYYYMMDD> --market CN --copy-other-feeds
```

Then run coverage audit:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\round533_external_feeds_lpr_repaired_<YYYYMMDD> --output-dir data\reports\round533_external_feed_lpr_repair_coverage_audit_<YYYYMMDD> --market CN
```

Stop unless the coverage audit shows:

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
- Do not overwrite existing long-cycle processed external-feed roots in place.

## Stop Or Rotate Conditions

- Stop if the analyst cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if required cross-machine quota packs are unavailable.
- Stop if LPR cache refresh does not produce non-missing `lpr_1y` and `lpr_5y`.
- Keep external LPR/macro factors blocked until LPR non-missing coverage is repaired and coverage audit passes.
