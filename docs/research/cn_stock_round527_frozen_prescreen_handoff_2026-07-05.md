# CN Stock Round527 Frozen Prescreen Handoff

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 24 after the Round504 review-agent baseline. This round did not call Tushare, did not run a quota dry-run, did not run the analyst prescreen, and did not create generated data. It prepared the exact handoff path for the frozen January-April 2024 analyst-report-revision prescreen that may run only after April cache evidence exists.

## Round Objective

Round526 left the same-day provider-backed April cache blocked by:

- `daily_provider_request_budget_exhausted`
- `missing_required_quota_pack_machines`

Missing required quota-pack machines remain:

- `highspec_desktop`
- `laptop`

The selected Round527 objective was therefore deliberately non-provider:

- Keep the April 2024 cache blocked on 2026-07-05.
- Do not repeat a same-day cache preflight with no new quota evidence.
- Verify the analyst-report-revision prescreen entrypoint and output fields.
- Record the frozen January-April command template and result-review checklist without running it.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks before this documentation work:

- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status: clean before edits.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Entry Point Verified

The analyst-report-revision prescreen entrypoint remains:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --help
```

The CLI requires:

- repeated `--report-root`
- `--stock-basic`
- optional `--bars-root`
- `--output-dir`
- `--analysis-start-date`
- `--analysis-end-date`
- `--horizons`
- `--execution-lag`
- `--pit-lag-trade-days`
- prescreen threshold arguments

Do not add `--include-final-holdout` for this source-quality prescreen.

The writer produces:

- `analyst_report_revision_prescreen.json`
- `analyst_report_revision_prescreen.md`
- `analyst_report_revision_prescreen_results.csv`
- `analyst_report_revision_prescreen_ic_observations.csv`
- `analyst_report_revision_prescreen_neutral_observations.csv`

Generated prescreen outputs stay under `data/reports` and stay out of Git.

## Current Evidence Baseline

The frozen command path is anchored to the existing January-March evidence:

| Evidence | Report rows | Report assets | Factor rows | Aligned rows | FDR-significant tests | Neutral-gate passes | Research leads | Promotion allowed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Round504 January-February | 3,498 | 1,317 | 6,882 | 13,764 | 5 | 4 | 0 | 0 |
| Round505 January-March | 5,132 | 1,511 | 9,966 | 19,932 | 0 | 2 | 0 | 0 |

Interpretation retained from Round506:

- Adding March weakened the evidence instead of strengthening it.
- Multiple-testing leads fell from 5 to 0.
- Research leads remained 0.
- The family may receive one more quota-aware monthly cache, but formulas, horizons, lags, and thresholds must stay frozen.

## April Cache Prerequisites

Do not run the frozen January-April prescreen until a real April 2024 cache succeeds.

The April cache is considered usable only when its cache summary shows:

- fetched windows: `1`
- failed windows: `0`
- rate-limited windows: `0`
- processed output directory exists under `data/processed`
- no row-cap warning requiring a smaller window rerun
- startup gates still have no blockers
- required quota-pack constraints are clear before the provider-backed fetch

Provider-backed April cache remains blocked until all of these are true:

- actual-date cache CLI dry-run exits `0`;
- `target_date_matches_generated_at=true`;
- `remaining_request_windows >= 1`;
- `missing_required_quota_pack_machines=[]`;
- `present_quota_pack_machines` includes `office_desktop`, `highspec_desktop`, and `laptop`;
- no `quota_target_date_differs_from_generated_at` warning appears;
- no `--skip-quota-preflight`;
- `--quota-pack-machine-note` is used only as audit context.

## Frozen January-April Prescreen Command

Run this only after April cache succeeds. Replace `<APRIL_CACHE_PROCESSED_ROOT>` with the actual processed output directory created by the successful April cache. Replace `<YYYYMMDD>` with the actual local date of the prescreen run.

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root <APRIL_CACHE_PROCESSED_ROOT> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round528_analyst_report_revision_prescreen_202401_202404_<YYYYMMDD> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Do not alter:

- factor formulas
- `--horizons 5,20`
- `--execution-lag 1`
- `--pit-lag-trade-days 1`
- cross-section, observation, industry, or amount thresholds
- final-holdout policy

## Result Review Checklist

After the command completes, inspect the terminal JSON and the written Markdown/JSON report for:

- stage: `analyst_report_revision_pit_prescreen`
- `holdout_policy.final_holdout_included=false`
- `data_window.report_rows`
- `data_window.report_assets`
- `data_window.min_report_date`
- `data_window.max_report_date`
- `data_window.min_signal_date`
- `data_window.max_signal_date`
- `summary.candidate_count`
- `summary.test_count`
- `summary.factor_rows`
- `summary.aligned_rows`
- `summary.multiple_testing_lead_count`
- `summary.neutral_gate_pass_count`
- `summary.research_lead_count`
- `summary.promotion_allowed_candidates`
- `summary.next_direction`

Write a lightweight docs report for the result. Do not commit the generated JSON/CSV/Markdown under `data/reports`.

## Decision Rules

If `summary.research_lead_count=0`, run a family review before any further cache work.

If `summary.multiple_testing_lead_count=0`, prepare rotation to a new PIT source candidate plan.

If any candidate appears promising only because of one narrow month, do not tune formulas to recover the signal.

If research leads appear, the next gate is reference de-dup and later walk-forward/cost/capacity/regime review. A prescreen lead is not portfolio evidence, promotion evidence, or live evidence.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run portfolio grids or promotion gates from this prescreen.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
