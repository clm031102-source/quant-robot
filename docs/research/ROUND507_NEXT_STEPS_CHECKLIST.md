# Round507 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-20260707`.

## Current State

- Current loop round: 4 after the Round504 review-agent baseline.
- Next review-agent checkpoint: round 10.
- Latest analyst source state: January-April 2024 cached and screened.
- Latest result: 0 research leads and 0 promotion-allowed candidates.
- Multiple-testing leads: 0.
- Neutral-gate pass count: 0.
- Main evidence change from Round505: adding April did not recover the source; neutral-gate pass count fell from 2 to 0.

## Red Lines

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover April results.
- Do not run portfolio grids or promotion gates.
- Do not commit generated `data/` outputs, Parquet/CSV files, logs, tokens, broker credentials, account data, or order data.
- Do not generate financial reporting timeliness factors from the 742-symbol Round638 cache.

## Default Next Path

Prefer rotation away from analyst-report-revision formula continuation.

1. Run startup context and gates:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-20260707
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-20260707
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-20260707 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

2. Run a family review or candidate-plan gate for a new PIT-safe source.

3. If continuing analyst-report history anyway, cache only one more monthly window with frozen formulas and no portfolio or promotion work:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-05-01 --end-date 2024-05-31 --output-dir data\reports\round508_analyst_report_revision_cache_202405_<date> --processed-output-dir data\processed\round508_analyst_report_revision_cache_202405_<date> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

4. Rerun the frozen prescreen only if the May cache succeeds and quota is clean:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_20260707 --report-root data\processed\round508_analyst_report_revision_cache_202405_<date> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round508_analyst_report_revision_prescreen_202401_202405_<date> --analysis-start-date 2024-01-01 --analysis-end-date 2024-07-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Stop Or Rotate Conditions

- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Rotate if January-May still has `research_lead_count=0`.
- Rotate if multiple-testing leads remain 0.
- Rotate if size-neutral or year-coverage blockers remain dominant after enough report history.

## Success Signs

- A new PIT source candidate plan clears candidate-plan gate before factor generation.
- For analyst continuation only: cache has 0 failed windows and 0 rate-limited windows.
- Prescreen has `passes=true` and all 4 candidate names with factor rows.
- A real research lead requires more than short-window IC: year coverage, neutral gates, and later cost/capacity/regime checks must clear.
