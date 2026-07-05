# Round504 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Red Lines

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
- Do not touch the 2026 final holdout for analyst-report source-smoke work.
- Do not claim a promoted or live strategy from Round503 or Round504 evidence.

## Current State

- Machine: `office_desktop`
- Task: `factor_batch`
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`
- Stable branch: `main`
- Primary research market: `CN_ETF`
- Current CN stock work: auxiliary factor batch / PIT source construction
- Latest completed action: February 2024 analyst `report_rc` cache plus frozen January-February PIT prescreen

## Default Next Path

Goal: extend analyst-report-revision PIT history without changing formulas.

Run only after provider quota should have reset.

1. Confirm startup context:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
```

2. Run Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
```

3. Run CN stock startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --market CN --asset-type stock --commits-allowed --pushes-allowed --confirm-start
```

4. Run CN stock data manifest:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --market CN
```

5. Cache the next report month:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-03-01 --end-date 2024-03-31 --output-dir data\reports\round505_analyst_report_revision_cache_202403_<date> --processed-output-dir data\processed\round505_analyst_report_revision_cache_202403_<date> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

6. Rerun the same frozen prescreen with January, February, and March report roots:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_<date> --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round505_analyst_report_revision_prescreen_202401_202403_<date> --analysis-start-date 2024-01-01 --analysis-end-date 2024-05-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

## Success Signs

- Cache has `failed_windows=0`.
- Cache has `rate_limited_windows=0`.
- Prescreen has `passes=true`.
- Prescreen reports all 4 candidate names with rows.
- `research_lead_count > 0` only after year coverage and neutral gates clear.
- `promotion_allowed_candidates` must remain 0 at this stage.

## Stop Points

- Stop if provider reports the same-day `2_per_day` limit or another rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate is not `cleared`.
- Stop if data manifest has blockers.
- Stop before any portfolio grid or promotion gate.

## Plain-English Terms

- PIT source: data that was available at the time, not learned from the future.
- Paper-ready: suitable for observation or documentation, not live trading.
- Promotion: moving a candidate toward official strategy status. This is disabled here.
- Final holdout: the recent 2026 data reserved for one-time final checks. Do not use it for tuning.
- Portfolio grid: trying many portfolio construction parameters. This is not allowed for the current analyst source smoke.
