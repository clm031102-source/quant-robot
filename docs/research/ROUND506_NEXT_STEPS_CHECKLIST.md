# Round506 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 3 after the Round504 review-agent baseline.
- Next review-agent checkpoint: round 10.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest local review: Round506 quota-aware review.
- Latest result: 0 research leads and 0 promotion-allowed candidates.
- Main evidence change from Round504 to Round505: adding March reduced multiple-testing leads from 5 to 0.
- Provider decision: no same-day third `report_rc` request on 2026-07-05 because Round467 documented a `2_per_day` limit and Round504/Round505 already made two successful monthly requests.

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

## Default Next Path

Continue only after provider quota plausibly resets. If provider quota is unclear, stop rather than retrying blindly.

1. Run startup context and gates:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

2. Cache April 2024 analyst reports once:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round507_analyst_report_revision_cache_202404_<date> --processed-output-dir data\processed\round507_analyst_report_revision_cache_202404_<date> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

3. Rerun the frozen prescreen with January-April roots:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_<date> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round507_analyst_report_revision_prescreen_202401_202404_<date> --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Stop Or Rotate Conditions

- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.
- Prepare rotation if size-neutral or year-coverage blockers remain dominant after enough report history.

## Success Signs

- Cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true`.
- Prescreen keeps all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
