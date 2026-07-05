# Round522 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 19 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round513 completed with Quant PM agent `Turing` and ordinary-user agent `Maxwell`.
- Next review-agent checkpoint: round 20 after the Round504 baseline, due in Round523.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota tooling: analyst-report quota preflight now summarizes explicit quota-pack provenance in packet JSON, Markdown, standalone CLI stdout, and cache CLI stdout.
- Latest provenance-aware preflight: `data\reports` plus `data\reports\round521_analyst_quota_pack_provenance_20260705` counted 2 same-day provider request windows, skipped 2 duplicate evidence rows, recorded `quota_pack_root_count=1`, surfaced `office_desktop/factor_batch/codex/factor-batch-cn-stock-profit-mining-20260704`, blocked with `daily_provider_request_budget_exhausted`, and exited `3`.
- Latest actual-date cache-CLI preflight-only: 2026-07-05 is blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, included the same pack provenance, and exits `3` before any Tushare fetch.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 96 unit tests, Python compile, project audit, and laptop project-sync audit.

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

## Quota Pack Provenance Rule

Quota preflight remains local-report-root evidence only. A quota pack helps another machine include this workstation's local evidence, but it is still not a global provider-quota guarantee.

When exporting a pack, include provenance:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\analyst_report_quota_pack_<machine>_<YYYYMMDD> --machine <machine> --task <task> --branch <current-branch>
```

When running preflight, pass pack roots explicitly:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --report-root <imported_pack_root_from_other_machine> --target-date <YYYY-MM-DD> --output-dir data\reports\quota_preflight_with_packs_<YYYYMMDD> --fail-on-blocked
```

The resulting preflight JSON/Markdown/stdout should include:

- `summary.quota_pack_root_count`
- `quota_pack_provenance`
- `summary.duplicate_evidence_rows`
- `duplicate_window_rows`
- all scanned `report_roots`

For the cache CLI, pass the same roots with repeated `--quota-report-root`:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round523_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round523_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root <imported_pack_root_from_other_machine> --quota-output-dir data\reports\round523_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

Notes:

- Share quota packs out of band; do not commit generated `data\reports` pack output.
- Explicit scans of pack roots count copied cache-summary evidence only once per source fingerprint.
- If cross-machine packs are unavailable, manually confirm no other workstation consumed same-day `report_rc` budget before provider-backed caching.

## Default Next Path

Round523 is the next required two-agent checkpoint after the Round504 baseline.

Before any new cache attempt, run:

1. Quant PM agent review of current analyst-report quota/tooling state.
2. Ordinary no-experience user review of the latest checklist and cache command safety.
3. Update the next target based on their findings.

If the review still recommends waiting for quota reset, do not run provider-backed cache. If it recommends a safe dry-run only, use:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round523_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round523_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root <imported_pack_root_from_other_machine> --quota-output-dir data\reports\round523_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

Stop if the safe dry-run exits `3`.

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

- Round523 two-agent checkpoint is completed and documented.
- Actual-date cache CLI preflight with local reports plus all available provenance-aware quota packs allows one request window and exits `0`.
- Terminal output and JSON evidence include `target_date_matches_generated_at=true`, `quota_scope="local_report_roots_only"`, `quota_pack_provenance`, `duplicate_evidence_rows`, `duplicate_window_rows`, and all scanned `report_roots`.
- April cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true`.
- Prescreen keeps all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
