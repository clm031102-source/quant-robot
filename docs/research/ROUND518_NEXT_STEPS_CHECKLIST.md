# Round518 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 15 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round513 completed with Quant PM agent `Turing` and ordinary-user agent `Maxwell`.
- Next review-agent checkpoint: round 20 after the Round504 baseline.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota tooling: analyst-report quota packs can export lightweight cache-summary evidence for cross-machine preflight use.
- Latest real quota pack export: `data\reports\round518_analyst_quota_pack_20260705`, with `exported_report_count=8`.
- Latest pack preflight: explicit pack scan blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and exited `3`.
- Latest actual-date cache-CLI preflight-only: 2026-07-05 is blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, and exits `3` before any Tushare fetch.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 91 unit tests, Python compile, project audit, and laptop project-sync audit.

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

## Cross-Machine Quota Pack Rule

Quota preflight remains local-report-root evidence only. A quota pack helps another machine include this workstation's local evidence, but it is still not a global provider-quota guarantee.

Export a pack from each active workstation:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\analyst_report_quota_pack_<machine>_<YYYYMMDD>
```

Use packs by passing each pack root explicitly:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --report-root <imported_pack_root_from_other_machine> --target-date <YYYY-MM-DD> --output-dir data\reports\quota_preflight_with_packs_<YYYYMMDD> --fail-on-blocked
```

For the cache CLI, pass the same roots with repeated `--quota-report-root`:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round519_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round519_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root <imported_pack_root_from_other_machine> --quota-output-dir data\reports\round519_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

Notes:

- Share quota packs out of band; do not commit generated `data\reports` pack output.
- Default broad scans such as `data\reports` skip quota-pack internals to avoid double-counting local copies.
- Explicit scans of a pack root count its copied cache-summary evidence.
- If cross-machine packs are unavailable, manually confirm no other workstation consumed same-day `report_rc` budget before provider-backed caching.

## Default Next Path

Only continue the analyst-report cache after the provider quota plausibly resets.

1. Run startup context and gates:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

2. Export or gather quota packs from every active workstation.

3. Safe dry-run only. This command does not call Tushare:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round519_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round519_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root <imported_pack_root_from_other_machine> --quota-output-dir data\reports\round519_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

4. Stop if the safe dry-run exits `3`.

5. Run the provider-backed cache only if the actual-date safe dry-run exits `0`. Remove only `--quota-preflight-only`, keep the same quota roots, and do not set a nonlocal `--quota-target-date`.

6. Rerun the frozen prescreen with January-April roots only after April cache succeeds:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round519_analyst_report_revision_cache_202404_<YYYYMMDD> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round519_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Stop Or Rotate Conditions

- Stop if the cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Stop if cross-machine quota packs are unavailable and same-day provider usage cannot be manually confirmed.
- Stop if `quota_target_date_differs_from_generated_at` appears during provider-backed cache execution.
- Stop if `skip_quota_preflight_requires_cached_processed_windows` appears; do not use skip to fetch missing windows.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.

## Success Signs

- Actual-date cache CLI preflight with local reports plus all available quota packs allows one request window and exits `0`.
- Terminal output and JSON evidence include `target_date_matches_generated_at=true`, `quota_scope="local_report_roots_only"`, and all scanned `report_roots`.
- April cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true`.
- Prescreen keeps all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
