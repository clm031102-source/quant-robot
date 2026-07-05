# Round516 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 13 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round513 completed with Quant PM agent `Turing` and ordinary-user agent `Maxwell`.
- Next review-agent checkpoint: round 20 after the Round504 baseline.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest tooling hardening: `--skip-quota-preflight` now requires every requested analyst-report window to have an existing local processed cache partition; otherwise it exits `3` before cache execution.
- Latest focused tests: `tests/unit/test_analyst_report_quota_preflight.py` passed with 16 tests.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 89 tests, Python compile, project audit, and laptop project-sync audit.
- Latest actual-date cache-CLI preflight-only: 2026-07-05 is blocked with `daily_provider_request_budget_exhausted` and exits `3` before any Tushare fetch.
- Latest skip guard evidence: skip with an empty processed-output directory is blocked with `skip_quota_preflight_requires_cached_processed_windows`.

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

## Skip-Quota Rule

`--skip-quota-preflight` is allowed only for offline cached replay.

- It still requires `--skip-quota-preflight-reason`.
- It requires `resume` and processed writes to remain enabled.
- It requires every requested `processed/analyst_report_rc_window` partition to exist under the selected processed-output directory.
- If any requested window is missing, the CLI exits `3` with `skip_quota_preflight_requires_cached_processed_windows`.
- Do not use skip to fetch from Tushare.

## Quota Date Rule

For provider-backed cache execution:

- Prefer omitting `--quota-target-date`; the CLI will use the local generated date.
- If `--quota-target-date` is supplied, it must equal the local generated date.
- If it differs, the CLI prints `quota_target_date_differs_from_generated_at`, exits `3`, and does not call the cache execution path.
- Nonlocal target dates are allowed for `--quota-preflight-only` and audit-only historical checks.

## Quota Scope Rule

Treat quota preflight as local evidence only.

- `quota_scope="local_report_roots_only"` means the preflight counted only the provided report roots.
- For one machine, the default `data\reports` root is enough to protect against repeated local requests.
- For multiple desktops, include every relevant workstation's exported report root with repeated `--quota-report-root` before trusting an allowed result.
- If cross-machine report roots are not available, manually confirm no other workstation consumed the same-day `report_rc` request budget before provider-backed caching.

## Default Next Path

Only continue the analyst-report cache after the provider quota plausibly resets.

1. Run startup context and gates:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

2. Safe dry-run only. This command does not call Tushare:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round517_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round517_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round517_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

3. Stop if the safe dry-run exits `3`.

4. Run the provider-backed cache only if the actual-date safe dry-run exits `0`. Remove only `--quota-preflight-only` and do not set a nonlocal `--quota-target-date`:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round517_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round517_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round517_cache_cli_quota_preflight_<YYYYMMDD>
```

5. Rerun the frozen prescreen with January-April roots only after April cache succeeds:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round517_analyst_report_revision_cache_202404_<YYYYMMDD> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round517_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Stop Or Rotate Conditions

- Stop if the cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Stop if `quota_target_date_differs_from_generated_at` appears during provider-backed cache execution.
- Stop if `skip_quota_preflight_requires_cached_processed_windows` appears; do not use skip to fetch missing windows.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.
- Prepare a cross-machine quota evidence plan before relying on local-only quota reports across multiple desktops.

## Success Signs

- Actual-date cache CLI preflight allows one request window and exits `0`.
- Terminal output and JSON evidence include `target_date_matches_generated_at=true`, `quota_scope="local_report_roots_only"`, and the scanned `report_roots`.
- April cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true`.
- Prescreen keeps all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
