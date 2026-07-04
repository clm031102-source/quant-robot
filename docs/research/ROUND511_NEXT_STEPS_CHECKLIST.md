# Round511 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 8 after the Round504 review-agent baseline.
- Next review-agent checkpoint: round 10.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest tooling hardening: `scripts/run_tushare_analyst_report_cache.py` runs local quota preflight by default, and `--skip-quota-preflight` now requires `--skip-quota-preflight-reason`.
- Latest skip-path test: local cached replay prints a `status="skipped"` audit packet before continuing.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 81 tests.
- Latest real cache-CLI preflight: 2026-07-05 is blocked with `daily_provider_request_budget_exhausted` and exits `3` before any Tushare fetch.

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
- If `--skip-quota-preflight` is ever used for an offline or controlled local replay, provide `--skip-quota-preflight-reason`.

## Default Next Path

Only continue the analyst-report cache after the provider quota plausibly resets.

1. Run startup context and gates:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

2. Cache April 2024 only if the cache CLI's default preflight exits `0`:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round512_analyst_report_revision_cache_202404_<date> --processed-output-dir data\processed\round512_analyst_report_revision_cache_202404_<date> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round512_cache_cli_quota_preflight_<date>
```

3. Rerun the frozen prescreen with January-April roots only after April cache succeeds:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round512_analyst_report_revision_cache_202404_<date> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round512_analyst_report_revision_prescreen_202401_202404_<date> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Stop Or Rotate Conditions

- Stop if the cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.

## Success Signs

- Cache CLI preflight allows one request window and exits `0`.
- Cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true`.
- Prescreen keeps all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
