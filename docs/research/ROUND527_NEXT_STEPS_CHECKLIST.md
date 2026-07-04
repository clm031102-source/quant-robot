# Round527 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 24 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota tooling: required quota-pack source machines and audit-only machine notes are supported.
- Latest quota state: Round526 safe cache-CLI dry-run with required machines and notes blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest Round527 work: frozen January-April prescreen handoff prepared without calling Tushare, without running a same-day quota dry-run, and without running prescreen.

## Next Best Target

If still on 2026-07-05, do not run provider-backed cache and do not repeat the same quota dry-run without new evidence.

The next useful work is one of:

- produce or import real quota packs from `highspec_desktop` and `laptop`;
- wait until the local quota date changes, then run one actual-date preflight with required-machine constraints;
- after a successful April cache, run the frozen January-April prescreen exactly once;
- if April cache remains blocked, prepare the next PIT source rotation plan without touching final holdout or portfolio grids.

Do not treat `--quota-pack-machine-note` as permission to cache.

## Before Any Command

Run these local gates first:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if any gate has blockers. The CN stock data manifest may return `review_required`; read warnings before continuing.

## Required-Machine Dry-Run

Run this only after the local quota date changes or after real cross-machine quota evidence is added:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round528_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round528_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round528_required_machine_quota_preflight_<YYYYMMDD> --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=<reason and timestamp if still unavailable>" --quota-pack-machine-note "laptop=<reason and timestamp if still unavailable>" --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

## Provider-Backed Cache Criteria

Run provider-backed April cache only when all of these are true:

- fresh gates have no blockers;
- actual-date cache CLI dry-run exits `0`;
- `target_date_matches_generated_at=true`;
- `remaining_request_windows >= 1`;
- all available quota packs are included with repeated `--quota-report-root`;
- `missing_required_quota_pack_machines=[]`;
- `present_quota_pack_machines` includes `office_desktop`, `highspec_desktop`, and `laptop`;
- no `quota_target_date_differs_from_generated_at` warning is present;
- no one proposes `--skip-quota-preflight`;
- `--quota-pack-machine-note` is used only as audit context.

## Frozen Prescreen Command

Run this only after April cache actually succeeds. Replace `<APRIL_CACHE_PROCESSED_ROOT>` with the processed output directory from the successful April cache.

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root <APRIL_CACHE_PROCESSED_ROOT> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round528_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Do not add `--include-final-holdout`.

## Prescreen Review Fields

Record these fields in a lightweight docs report:

- `holdout_policy.final_holdout_included`
- `data_window.report_rows`
- `data_window.report_assets`
- `data_window.min_report_date`
- `data_window.max_report_date`
- `summary.candidate_count`
- `summary.test_count`
- `summary.factor_rows`
- `summary.aligned_rows`
- `summary.multiple_testing_lead_count`
- `summary.neutral_gate_pass_count`
- `summary.research_lead_count`
- `summary.promotion_allowed_candidates`
- `summary.next_direction`

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
- Do not use `--continue-after-rate-limit` in this quota-constrained analyst-report path.
- Do not use nonlocal `--quota-target-date` for provider-backed cache execution.

## Stop Or Rotate Conditions

- Stop if the cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Stop if required cross-machine quota packs are unavailable.
- Stop if `quota_target_date_differs_from_generated_at` appears during provider-backed cache execution.
- Stop if `skip_quota_preflight_requires_cached_processed_windows` appears; do not use skip to fetch missing windows.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.
