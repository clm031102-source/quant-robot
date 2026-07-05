# Round528 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 25 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota state: Round526 safe cache-CLI dry-run with required machines and notes blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest Round527 work: frozen January-April prescreen handoff prepared without provider calls.
- Latest Round528 work: local external-feed source audit completed without provider calls.

## Next Best Target

If still on 2026-07-05, do not run provider-backed analyst cache and do not repeat the same quota dry-run without new cross-machine quota evidence.

The next useful work is one of:

- produce or import real quota packs from `highspec_desktop` and `laptop`;
- wait until the local quota date changes, then run one actual-date analyst preflight with required-machine constraints;
- after successful April analyst cache, run the frozen January-April prescreen exactly once;
- if analyst cache remains blocked, write an external-feed family review using Round528 source-audit evidence, without preregistering new factors yet.

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
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round529_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round529_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round529_required_machine_quota_preflight_<YYYYMMDD> --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=<reason and timestamp if still unavailable>" --quota-pack-machine-note "laptop=<reason and timestamp if still unavailable>" --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

## Frozen Analyst Prescreen

Run this only after April cache actually succeeds. Replace `<APRIL_CACHE_PROCESSED_ROOT>` with the processed output directory from the successful April cache.

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root <APRIL_CACHE_PROCESSED_ROOT> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round529_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Do not add `--include-final-holdout`.

## External-Feed Source Audit Recap

Round528 local coverage audit:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --output-dir data\reports\round528_external_feed_coverage_audit_20260705 --market CN
```

Observed result:

- `external_hk_hold`: pass, 134,461 rows, 40 observation dates, 3,980 symbols, median gap 1.0 day.
- `external_macro_rates`: blocked by `lpr_non_missing_coverage_below_threshold`; SHIBOR complete rows 340, LPR non-null rows 0.
- External-feed IC or portfolio allowed: false.

Round528 minimal join smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round528_external_feed_join_smoke_202407_20260705 --market CN --signal-start-date 2024-07-01 --signal-end-date 2024-07-31
```

Observed result:

- Seed count: 6
- Pass count: 6
- Joined rows: 428,856
- Available-date violations: 0
- Same-day or future raw-date violations: 0
- Promotion allowed: false

Do not rerun full-window join smoke in a normal loop turn unless the implementation is optimized or an intentionally long timeout is acceptable; the Round528 full-window attempt timed out.

## External-Feed Review Boundary

Before any external-feed preregistration, write a family review that reads:

- `docs/research/cn_stock_round190_192_three_round_review_2026-06-23.md`
- `docs/research/cn_stock_round213_external_northbound_crowding_reversal_prescreen_2026-06-24.md`
- `docs/research/cn_stock_round450_452_three_round_audit_2026-06-27.md`
- `docs/research/cn_stock_round528_external_feed_rotation_source_audit_2026-07-05.md`

Allowed external-feed continuation:

- HK-hold coverage may be reviewed as source-quality evidence.
- SHIBOR may be reviewed only as a regime-control input after long-cycle validation.
- Any factor idea must be genuinely new and preregistered before testing.

Blocked external-feed continuation:

- no old positive northbound accumulation rerun;
- no old northbound crowding/reversal rerun without a new mechanism;
- no margin-credit reentry without a fresh review of prior failures;
- no LPR factor until LPR coverage clears;
- no portfolio grid, promotion gate, or final-holdout read from source audit or join smoke.

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
- Run a family review if January-April analyst prescreen still has `research_lead_count=0`.
- Prepare rotation if analyst multiple-testing leads remain 0.
- Keep external LPR/macro factors blocked until LPR non-missing coverage is repaired.
