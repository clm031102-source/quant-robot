# CN Stock Round507 Analyst Report Revision April Extension

Date: 2026-07-07

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-20260707`

Scope: continue the analyst-report-revision PIT source by adding April 2024 and rerunning the same frozen prescreen. This remains research-to-review only: no broker connection, no live account reads, no order placement, and no automatic live trading.

## Startup Evidence

Startup gates were rerun from the current task branch before provider work:

- `pre-alpha` completion gate cleared on `main` after Round638 was fast-forwarded into `main` and the absorbed remote topic branch was removed.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary research market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Source Cache

Quota preflight allowed one April `report_rc` request on 2026-07-07:

- Status: `allowed`.
- Counted same-day provider request windows: 0.
- Remaining request windows: 2.
- Warning: `local_report_roots_only`.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round507_analyst_report_revision_cache_202404_20260707 --processed-output-dir data\processed\round507_analyst_report_revision_cache_202404_20260707 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-output-dir data\reports\round507_analyst_report_quota_preflight_20260707
```

Result:

- Windows: 1.
- Fetched windows: 1.
- Failed windows: 0.
- Rate-limited windows: 0.
- Row-cap warning windows: 0.
- Rows: 1,696.
- Assets: 876.
- Min report date: 2024-04-29.
- Max report date: 2024-04-30.
- Processed output: `data\processed\round507_analyst_report_revision_cache_202404_20260707`.

Generated data stays out of Git.

## Frozen PIT Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_20260707 --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round507_analyst_report_revision_prescreen_202401_202404_20260707 --analysis-start-date 2024-01-01 --analysis-end-date 2024-06-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Result:

- Stage: `analyst_report_revision_pit_prescreen`.
- Final holdout included: false.
- Report rows: 6,828.
- Report assets: 1,789.
- Max report date: 2024-04-30.
- Max signal date: 2024-05-06.
- Candidates: 4.
- Tests: 8.
- Factor rows: 13,594.
- Aligned rows: 27,188.
- Multiple-testing lead count: 0.
- Neutral-gate pass count: 0.
- Research lead count: 0.
- Promotion-allowed candidates: 0.
- Next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`.

Top diagnostics after adding April:

| Candidate | Horizon | Mean IC | ICIR | IC t-stat | Positive IC rate | Quantile spread | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `analyst_target_upside_60` | 5 | 0.08475782766808128 | 0.27280396934486717 | 1.1574092199501758 | 0.6666666666666666 | 0.00968265503337529 | false |
| `analyst_eps_revision_90` | 20 | 0.06207176812576497 | 0.4631702162542569 | 1.965064804542148 | 0.6666666666666666 | 0.01664490120289321 | false |
| `analyst_np_revision_90` | 20 | 0.060699878553516315 | 0.44167781285378854 | 1.8738802594113404 | 0.6666666666666666 | 0.02132927101273632 | false |
| `analyst_revision_target_composite_90` | 5 | 0.05257119430014964 | 0.423458381433133 | 1.7965817583698875 | 0.7222222222222222 | 0.010224298929552175 | false |

## Interpretation

Adding April did not restore the Round504 short-window promise. Compared with Round505, the family remains at zero multiple-testing leads and zero research leads, and neutral-gate pass count fell from 2 to 0. The best raw IC rows are not enough because FDR, size-neutral, year-coverage, later walk-forward/cost/capacity/regime, and final-holdout gates remain unmet.

Do not tune analyst formulas, horizons, lags, report fields, or thresholds to recover this source. Do not run portfolio grids or promotion gates.

## Decision

The analyst-report-revision source should rotate unless there is an explicit decision to spend one more quota-limited monthly cache for source-history coverage only. A new PIT source candidate plan is preferred before further factor generation.

Allowed next actions:

- Run a family review for the analyst-report-revision source and mark formula tuning as blocked.
- Register a genuinely new PIT-safe source candidate plan before any new factor generation.
- Optionally cache at most one more month only as source-history coverage, with the same frozen formulas and no portfolio or promotion work.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
- Do not use 2026 final holdout for this source-smoke work.
